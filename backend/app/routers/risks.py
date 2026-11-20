from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..audit import describe_changes, log_action
from ..models import Asset, Process, Risk, User
from ..database import get_db
from ..deps import get_current_user, require_role
from ..models import Asset, Process, Risk
from ..schemas import RiskCreate, RiskOut, RiskUpdate
from ..scoring import compute_score, risk_level

router = APIRouter(prefix="/api/risks", tags=["Risques"],
                   dependencies=[Depends(get_current_user)])
writer = Depends(require_role("admin", "analyste"))

LEVELS = {"Faible": (1, 4), "Moyen": (5, 9), "Élevé": (10, 15), "Critique": (16, 25)}
Level = Literal["Faible", "Moyen", "Élevé", "Critique"]


def _get(db: Session, risk_id: int) -> Risk:
    risk = db.get(Risk, risk_id)
    if risk is None:
        raise HTTPException(404, "Risque introuvable")
    return risk


def _check_asset(db: Session, asset_id: int | None) -> None:
    if asset_id is not None and db.get(Asset, asset_id) is None:
        raise HTTPException(404, "Actif introuvable")


@router.get("", response_model=list[RiskOut])
def list_risks(process_id: int | None = None, asset_id: int | None = None,
               level: Level | None = None, db: Session = Depends(get_db)):
    query = select(Risk).order_by(Risk.score.desc(), Risk.id)
    if process_id is not None:
        query = query.where(Risk.process_id == process_id)
    if asset_id is not None:
        query = query.where(Risk.asset_id == asset_id)
    if level is not None:
        low, high = LEVELS[level]
        query = query.where(Risk.score.between(low, high))
    return [RiskOut.model_validate(r) for r in db.scalars(query)]


# Doit être déclarée AVANT "/{risk_id}", sinon "matrix" serait pris pour un id
@router.get("/matrix")
def risk_matrix(process_id: int | None = None, db: Session = Depends(get_db)):
    query = select(Risk.probability, Risk.impact, func.count()).group_by(Risk.probability, Risk.impact)
    if process_id is not None:
        query = query.where(Risk.process_id == process_id)
    counts = {(p, i): n for p, i, n in db.execute(query)}

    cells, by_level = [], {level: 0 for level in LEVELS}
    for probability in range(5, 0, -1):          # de la ligne 5 (haut) à 1 (bas)
        for impact in range(1, 6):
            count = counts.get((probability, impact), 0)
            score = compute_score(probability, impact)
            level = risk_level(score)
            by_level[level] += count
            cells.append({"probability": probability, "impact": impact,
                          "score": score, "level": level, "count": count})
    return {"cells": cells, "by_level": by_level, "total": sum(by_level.values())}


@router.get("/{risk_id}", response_model=RiskOut)
def get_risk(risk_id: int, db: Session = Depends(get_db)):
    return RiskOut.model_validate(_get(db, risk_id))


@router.post("", response_model=RiskOut, status_code=201, dependencies=[writer])
def create_risk(data: RiskCreate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    if db.get(Process, data.process_id) is None:
        raise HTTPException(404, "Processus introuvable")
    _check_asset(db, data.asset_id)
    risk = Risk(**data.model_dump(), score=compute_score(data.probability, data.impact))
    db.add(risk)
    db.flush()  # donne risk.id sans valider la transaction
    log_action(db, user, "création", "risque", risk.id,
               f"{risk.threat} (score {risk.score})")
    db.commit()
    db.refresh(risk)
    return RiskOut.model_validate(risk)


@router.put("/{risk_id}", response_model=RiskOut, dependencies=[writer])
def update_risk(risk_id: int, data: RiskUpdate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    risk = _get(db, risk_id)
    changes = {k: v for k, v in data.model_dump(exclude_unset=True).items()
               if v is not None or k == "asset_id"}
    if "asset_id" in changes:
        _check_asset(db, changes["asset_id"])
    details = describe_changes(risk, changes)      # AVANT les setattr
    for key, value in changes.items():
        setattr(risk, key, value)
    risk.score = compute_score(risk.probability, risk.impact)  # toujours recalculé côté serveur
    log_action(db, user, "modification", "risque", risk.id, details)
    db.commit()
    db.refresh(risk)
    return RiskOut.model_validate(risk)


@router.delete("/{risk_id}", status_code=204, dependencies=[writer])
def delete_risk(risk_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    risk = _get(db, risk_id)
    # On note le contenu AVANT de supprimer, sinon on ne saura plus ce qui a disparu
    log_action(db, user, "suppression", "risque", risk.id,
               f"{risk.threat} (score {risk.score})")
    db.delete(risk)
    db.commit()
