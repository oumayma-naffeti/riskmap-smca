from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import describe_changes, log_action
from ..database import get_db
from ..deps import get_current_user, require_role
from ..kri_models import KRI, KRIMeasure
from ..kri_schemas import (KRICreate, KRIOut, KRIUpdate, MeasureCreate,
                           MeasureOut)
from ..models import Risk

router = APIRouter(
    prefix="/api",
    tags=["KRI"],
    dependencies=[Depends(get_current_user)],
)

writer = Depends(require_role("admin", "analyste"))


def _get_risk(db: Session, risk_id: int) -> Risk:
    risk = db.get(Risk, risk_id)
    if risk is None:
        raise HTTPException(404, "Risque introuvable")
    return risk


def _get_kri(db: Session, kri_id: int) -> KRI:
    kri = db.get(KRI, kri_id)
    if kri is None:
        raise HTTPException(404, "KRI introuvable")
    return kri


def _state(kri: KRI, value: float | None) -> str:
    if value is None:
        return "sans mesure"
    breached = value > kri.threshold if kri.alert_when == "au-dessus" else value < kri.threshold
    return "alerte" if breached else "normal"


def _out(db: Session, kri: KRI) -> KRIOut:
    last = db.scalars(
        select(KRIMeasure).where(KRIMeasure.kri_id == kri.id)
        .order_by(KRIMeasure.measured_at.desc(), KRIMeasure.id.desc()).limit(1)
    ).first()
    value = last.value if last else None
    return KRIOut(
        id=kri.id, risk_id=kri.risk_id, name=kri.name, unit=kri.unit,
        threshold=kri.threshold, alert_when=kri.alert_when, owner=kri.owner,
        description=kri.description, last_value=value,
        last_measured_at=last.measured_at if last else None,
        state=_state(kri, value),
    )


@router.get("/kris", response_model=list[KRIOut])
def list_all_kris(db: Session = Depends(get_db)):
    return [_out(db, k) for k in db.scalars(select(KRI).order_by(KRI.id)).all()]


@router.get("/risks/{risk_id}/kris", response_model=list[KRIOut])
def list_kris(risk_id: int, db: Session = Depends(get_db)):
    _get_risk(db, risk_id)
    rows = db.scalars(select(KRI).where(KRI.risk_id == risk_id).order_by(KRI.id)).all()
    return [_out(db, k) for k in rows]


@router.post("/risks/{risk_id}/kris", response_model=KRIOut,
             status_code=201, dependencies=[writer])
def create_kri(risk_id: int, data: KRICreate, db: Session = Depends(get_db),
               user=Depends(get_current_user)):
    risk = _get_risk(db, risk_id)
    kri = KRI(risk_id=risk_id, **data.model_dump())
    db.add(kri)
    db.flush()
    log_action(db, user, "création", "kri", kri.id,
               f"{kri.name} (alerte {kri.alert_when} {kri.threshold}) sur "
               f"{risk.code or 'risque #' + str(risk.id)}")
    db.commit()
    db.refresh(kri)
    return _out(db, kri)


@router.put("/kris/{kri_id}", response_model=KRIOut, dependencies=[writer])
def update_kri(kri_id: int, data: KRIUpdate, db: Session = Depends(get_db),
               user=Depends(get_current_user)):
    kri = _get_kri(db, kri_id)
    changes = data.model_dump(exclude_unset=True)
    for field in ("name", "threshold", "alert_when"):  # obligatoires
        if field in changes and changes[field] is None:
            changes.pop(field)
    details = describe_changes(kri, changes)
    if details == "aucun changement":
        return _out(db, kri)
    for key, value in changes.items():
        setattr(kri, key, value)
    log_action(db, user, "modification", "kri", kri.id, details)
    db.commit()
    db.refresh(kri)
    return _out(db, kri)


@router.delete("/kris/{kri_id}", status_code=204,
               dependencies=[Depends(require_role("admin"))])
def delete_kri(kri_id: int, db: Session = Depends(get_db),
               user=Depends(get_current_user)):
    kri = _get_kri(db, kri_id)
    log_action(db, user, "suppression", "kri", kri.id, kri.name)
    db.delete(kri)
    db.commit()


@router.get("/kris/{kri_id}/measures", response_model=list[MeasureOut])
def list_measures(kri_id: int, db: Session = Depends(get_db)):
    _get_kri(db, kri_id)
    query = (select(KRIMeasure).where(KRIMeasure.kri_id == kri_id)
             .order_by(KRIMeasure.measured_at.desc(), KRIMeasure.id.desc()))
    return db.scalars(query).all()


@router.post("/kris/{kri_id}/measures", response_model=MeasureOut,
             status_code=201, dependencies=[writer])
def add_measure(kri_id: int, data: MeasureCreate, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    kri = _get_kri(db, kri_id)
    measured_at = data.measured_at or date.today()
    if measured_at > date.today():
        raise HTTPException(422, "La date de mesure ne peut pas être dans le futur")
    measure = KRIMeasure(kri_id=kri_id, value=data.value,
                         measured_at=measured_at, comment=data.comment)
    db.add(measure)
    db.flush()
    state = _state(kri, measure.value)
    log_action(db, user, "création", "mesure kri", measure.id,
               f"{kri.name} : {measure.value} {kri.unit or ''} le {measured_at} ({state})".replace("  ", " "))
    db.commit()
    db.refresh(measure)
    return measure
