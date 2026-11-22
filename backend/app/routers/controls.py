from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import describe_changes, log_action
from ..control_models import Control
from ..control_schemas import ControlCreate, ControlOut, ControlUpdate
from ..database import get_db
from ..deps import get_current_user, require_role
from ..models import Risk

router = APIRouter(
    prefix="/api",
    tags=["Contrôles"],
    dependencies=[Depends(get_current_user)],
)

writer = Depends(require_role("admin", "analyste"))


def _get_risk(db: Session, risk_id: int) -> Risk:
    risk = db.get(Risk, risk_id)
    if risk is None:
        raise HTTPException(404, "Risque introuvable")
    return risk


def _get_control(db: Session, control_id: int) -> Control:
    control = db.get(Control, control_id)
    if control is None:
        raise HTTPException(404, "Contrôle introuvable")
    return control


@router.get("/controls", response_model=list[ControlOut])
def list_all_controls(db: Session = Depends(get_db)):
    return db.scalars(select(Control).order_by(Control.id)).all()


@router.get("/risks/{risk_id}/controls", response_model=list[ControlOut])
def list_controls(risk_id: int, db: Session = Depends(get_db)):
    _get_risk(db, risk_id)
    query = select(Control).where(Control.risk_id == risk_id).order_by(Control.id)
    return db.scalars(query).all()


@router.post("/risks/{risk_id}/controls", response_model=ControlOut,
             status_code=201, dependencies=[writer])
def create_control(risk_id: int, data: ControlCreate,
                   db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    risk = _get_risk(db, risk_id)
    control = Control(risk_id=risk_id, **data.model_dump())
    db.add(control)
    db.flush()
    log_action(db, user, "création", "contrôle", control.id,
               f"{control.name} ({control.control_type}) sur {risk.code or 'risque #' + str(risk.id)}")
    db.commit()
    db.refresh(control)
    return control


@router.put("/controls/{control_id}", response_model=ControlOut, dependencies=[writer])
def update_control(control_id: int, data: ControlUpdate,
                   db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    control = _get_control(db, control_id)
    changes = data.model_dump(exclude_unset=True)

    # Ces champs sont obligatoires : une valeur vide est ignorée
    for field in ("name", "control_type", "effectiveness"):
        if field in changes and not changes[field]:
            changes.pop(field)

    last = changes.get("last_test_date", control.last_test_date)
    nxt = changes.get("next_test_date", control.next_test_date)
    if last and nxt and nxt < last:
        raise HTTPException(422, "La date du prochain test précède celle du dernier test")

    details = describe_changes(control, changes)
    if details == "aucun changement":
        return control

    for key, value in changes.items():
        setattr(control, key, value)
    log_action(db, user, "modification", "contrôle", control.id, details)
    db.commit()
    db.refresh(control)
    return control


@router.delete("/controls/{control_id}", status_code=204,
               dependencies=[Depends(require_role("admin"))])
def delete_control(control_id: int, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    control = _get_control(db, control_id)
    log_action(db, user, "suppression", "contrôle", control.id, control.name)
    db.delete(control)
    db.commit()
