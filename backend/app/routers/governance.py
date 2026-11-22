from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..database import get_db
from ..deps import get_current_user, require_role
from ..governance_models import SMCAProgram
from ..models import User

router = APIRouter(
    prefix="/api/governance/program",
    tags=["Gouvernance SMCA"],
    dependencies=[Depends(get_current_user)],
)

writer = Depends(require_role("admin", "analyste"))
admin_only = Depends(require_role("admin"))

ENTITY = "programme SMCA"
BROUILLON, SOUMIS, APPROUVE, REFUSE = "brouillon", "soumis", "approuvé", "refusé"


class ProgramInput(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    scope: str = Field(min_length=10)
    objectives: str = Field(min_length=10)
    exclusions: str | None = None
    stakeholders: str | None = None
    owner: str | None = None


class ProgramOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    scope: str
    objectives: str
    exclusions: str | None
    stakeholders: str | None
    owner: str | None
    approval_status: str
    submitted_by: str | None
    submitted_at: datetime | None
    approved_by: str | None
    approved_at: datetime | None
    updated_at: datetime


def _get(db: Session) -> SMCAProgram | None:
    return db.scalar(select(SMCAProgram).order_by(SMCAProgram.id))


def _require(db: Session) -> SMCAProgram:
    program = _get(db)
    if program is None:
        raise HTTPException(404, "Programme SMCA introuvable")
    return program


@router.get("", response_model=ProgramOut | None)
def read_program(db: Session = Depends(get_db)):
    return _get(db)


@router.put("", response_model=ProgramOut, dependencies=[writer])
def save_program(data: ProgramInput, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    values = data.model_dump()
    program = _get(db)

    if program is None:
        program = SMCAProgram(**values, approval_status=BROUILLON)
        db.add(program)
        db.flush()
        log_action(db, user, "création", ENTITY, program.id, "programme créé (brouillon)")
    else:
        changed = [k for k, v in values.items() if getattr(program, k) != v]
        if not changed:
            return program  # rien n'a changé : on ne casse pas une approbation existante
        previous = program.approval_status
        for key, value in values.items():
            setattr(program, key, value)
        # Toute modification annule la validation précédente
        program.approval_status = BROUILLON
        program.submitted_by = None
        program.submitted_at = None
        program.approved_by = None
        program.approved_at = None
        log_action(db, user, "modification", ENTITY, program.id,
                   f"champs modifiés : {', '.join(changed)} (statut {previous} → {BROUILLON})")

    db.commit()
    db.refresh(program)
    return program


@router.post("/submit", response_model=ProgramOut, dependencies=[writer])
def submit_program(db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    program = _require(db)
    if program.approval_status not in (BROUILLON, REFUSE):
        raise HTTPException(409, "Seul un brouillon ou un programme refusé peut être soumis")

    program.approval_status = SOUMIS
    program.submitted_by = user.username
    program.submitted_at = func.now()
    log_action(db, user, "soumission", ENTITY, program.id, "soumis pour validation")
    db.commit()
    db.refresh(program)
    return program


@router.post("/approve", response_model=ProgramOut, dependencies=[admin_only])
def approve_program(db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    program = _require(db)
    if program.approval_status != SOUMIS:
        raise HTTPException(409, "Le programme doit être soumis avant approbation")
    if program.submitted_by == user.username:
        raise HTTPException(
            403, "Séparation des tâches : celui qui soumet le programme ne peut pas l'approuver")

    program.approval_status = APPROUVE
    program.approved_by = user.username
    program.approved_at = func.now()
    log_action(db, user, "approbation", ENTITY, program.id,
               f"approuvé par {user.username} (soumis par {program.submitted_by})")
    db.commit()
    db.refresh(program)
    return program


@router.post("/reject", response_model=ProgramOut, dependencies=[admin_only])
def reject_program(db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    program = _require(db)
    if program.approval_status != SOUMIS:
        raise HTTPException(409, "Seul un programme soumis peut être refusé")

    program.approval_status = REFUSE
    program.approved_by = None
    program.approved_at = None
    log_action(db, user, "refus", ENTITY, program.id,
               f"refusé par {user.username} (soumis par {program.submitted_by})")
    db.commit()
    db.refresh(program)
    return program
