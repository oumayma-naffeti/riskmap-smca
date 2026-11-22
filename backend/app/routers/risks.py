from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit import describe_changes, log_action
from ..database import get_db
from ..deps import get_current_user, require_role
from ..models import Asset, Process, Risk, User
from ..schemas import RiskCreate, RiskOut, RiskUpdate
from ..scoring import compute_score, risk_level


router = APIRouter(
    prefix="/api/risks",
    tags=["Risques"],
    dependencies=[Depends(get_current_user)],
)

writer = Depends(require_role("admin", "analyste"))

LEVELS = {
    "Faible": (1, 4),
    "Moyen": (5, 9),
    "Élevé": (10, 15),
    "Critique": (16, 25),
}

Level = Literal["Faible", "Moyen", "Élevé", "Critique"]


# Champs pouvant recevoir explicitement une valeur NULL
NULLABLE_RISK_FIELDS = {
    "asset_id",
    "code",
    "name",
    "category",
    "causes",
    "consequence",
    "source",
    "existing_measures",
    "owner",
    "review_date",
}


def _get(db: Session, risk_id: int) -> Risk:
    risk = db.get(Risk, risk_id)

    if risk is None:
        raise HTTPException(404, "Risque introuvable")

    return risk


def _check_asset(db: Session, asset_id: int | None) -> None:
    if asset_id is not None and db.get(Asset, asset_id) is None:
        raise HTTPException(404, "Actif introuvable")


def _check_process(db: Session, process_id: int) -> None:
    if db.get(Process, process_id) is None:
        raise HTTPException(404, "Processus introuvable")


# ---------- Liste des risques ----------

@router.get("", response_model=list[RiskOut])
def list_risks(
    process_id: int | None = None,
    asset_id: int | None = None,
    level: Level | None = None,
    db: Session = Depends(get_db),
):
    query = select(Risk).order_by(Risk.score.desc(), Risk.id)

    if process_id is not None:
        query = query.where(Risk.process_id == process_id)

    if asset_id is not None:
        query = query.where(Risk.asset_id == asset_id)

    if level is not None:
        low, high = LEVELS[level]
        query = query.where(Risk.score.between(low, high))

    risks = db.scalars(query).all()

    return [RiskOut.model_validate(risk) for risk in risks]


# ---------- Matrice des risques ----------
# Cette route doit rester avant /{risk_id}

@router.get("/matrix")
def risk_matrix(
    process_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = (
        select(
            Risk.probability,
            Risk.impact,
            func.count(),
        )
        .group_by(Risk.probability, Risk.impact)
    )

    if process_id is not None:
        query = query.where(Risk.process_id == process_id)

    counts = {
        (probability, impact): count
        for probability, impact, count in db.execute(query)
    }

    cells = []
    by_level = {level: 0 for level in LEVELS}

    for probability in range(5, 0, -1):
        for impact in range(1, 6):
            count = counts.get((probability, impact), 0)

            score = compute_score(probability, impact)
            level = risk_level(score)

            by_level[level] += count

            cells.append({
                "probability": probability,
                "impact": impact,
                "score": score,
                "level": level,
                "count": count,
            })

    return {
        "cells": cells,
        "by_level": by_level,
        "total": sum(by_level.values()),
    }


# ---------- Consultation d'un risque ----------

@router.get("/{risk_id}", response_model=RiskOut)
def get_risk(
    risk_id: int,
    db: Session = Depends(get_db),
):
    risk = _get(db, risk_id)

    return RiskOut.model_validate(risk)


# ---------- Création d'un risque ----------

@router.post(
    "",
    response_model=RiskOut,
    status_code=201,
    dependencies=[writer],
)
def create_risk(
    data: RiskCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _check_process(db, data.process_id)
    _check_asset(db, data.asset_id)

    risk_data = data.model_dump()

    risk = Risk(
        **risk_data,
        score=compute_score(
            data.probability,
            data.impact,
        ),
    )

    db.add(risk)
    db.flush()

    log_action(
        db,
        user,
        "création",
        "risque",
        risk.id,
        f"{risk.threat} (score {risk.score})",
    )

    db.commit()
    db.refresh(risk)

    return RiskOut.model_validate(risk)


# ---------- Modification d'un risque ----------

@router.put(
    "/{risk_id}",
    response_model=RiskOut,
    dependencies=[writer],
)
def update_risk(
    risk_id: int,
    data: RiskUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    risk = _get(db, risk_id)

    submitted_data = data.model_dump(exclude_unset=True)

    changes = {
        key: value
        for key, value in submitted_data.items()
        if value is not None or key in NULLABLE_RISK_FIELDS
    }

    if "asset_id" in changes:
        _check_asset(db, changes["asset_id"])

    details = describe_changes(risk, changes)

    for key, value in changes.items():
        setattr(risk, key, value)

    # Recalcul du score côté serveur
    risk.score = compute_score(
        risk.probability,
        risk.impact,
    )

    log_action(
        db,
        user,
        "modification",
        "risque",
        risk.id,
        details,
    )

    db.commit()
    db.refresh(risk)

    return RiskOut.model_validate(risk)


# ---------- Suppression d'un risque ----------

@router.delete(
    "/{risk_id}",
    status_code=204,
    dependencies=[writer],
)
def delete_risk(
    risk_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    risk = _get(db, risk_id)

    log_action(
        db,
        user,
        "suppression",
        "risque",
        risk.id,
        f"{risk.threat} (score {risk.score})",
    )

    db.delete(risk)
    db.commit()
