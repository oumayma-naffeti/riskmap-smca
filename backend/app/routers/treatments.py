from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_role
from ..models import Risk, Treatment
from ..schemas import TreatmentCreate, TreatmentOut, TreatmentUpdate

router = APIRouter(
    prefix="/api",
    tags=["Traitement des risques"],
    dependencies=[Depends(get_current_user)],
)

writer = Depends(require_role("admin", "analyste"))


def get_risk(db: Session, risk_id: int) -> Risk:
    risk = db.get(Risk, risk_id)
    if risk is None:
        raise HTTPException(status_code=404, detail="Risque introuvable")
    return risk


def get_treatment(db: Session, treatment_id: int) -> Treatment:
    treatment = db.get(Treatment, treatment_id)
    if treatment is None:
        raise HTTPException(status_code=404, detail="Traitement introuvable")
    return treatment


def validate_residual(probability, impact):
    if (probability is None) != (impact is None):
        raise HTTPException(
            status_code=422,
            detail="La probabilité et l'impact résiduels doivent être renseignés ensemble",
        )


@router.get("/risks/{risk_id}/treatments", response_model=list[TreatmentOut])
def list_treatments(risk_id: int, db: Session = Depends(get_db)):
    get_risk(db, risk_id)
    query = (
        select(Treatment)
        .where(Treatment.risk_id == risk_id)
        .order_by(Treatment.id)
    )
    return db.scalars(query).all()


@router.post(
    "/risks/{risk_id}/treatments",
    response_model=TreatmentOut,
    status_code=201,
    dependencies=[writer],
)
def create_treatment(
    risk_id: int,
    data: TreatmentCreate,
    db: Session = Depends(get_db),
):
    get_risk(db, risk_id)
    validate_residual(data.residual_probability, data.residual_impact)

    treatment = Treatment(risk_id=risk_id, **data.model_dump())
    db.add(treatment)
    db.commit()
    db.refresh(treatment)
    return treatment


@router.put(
    "/treatments/{treatment_id}",
    response_model=TreatmentOut,
    dependencies=[writer],
)
def update_treatment(
    treatment_id: int,
    data: TreatmentUpdate,
    db: Session = Depends(get_db),
):
    treatment = get_treatment(db, treatment_id)
    changes = data.model_dump(exclude_unset=True)

    probability = changes.get(
        "residual_probability", treatment.residual_probability
    )
    impact = changes.get("residual_impact", treatment.residual_impact)
    validate_residual(probability, impact)

    for key, value in changes.items():
        setattr(treatment, key, value)

    db.commit()
    db.refresh(treatment)
    return treatment


@router.delete(
    "/treatments/{treatment_id}",
    status_code=204,
    dependencies=[Depends(require_role("admin"))],
)
def delete_treatment(treatment_id: int, db: Session = Depends(get_db)):
    treatment = get_treatment(db, treatment_id)
    db.delete(treatment)
    db.commit()
