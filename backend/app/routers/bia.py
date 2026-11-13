from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_role
from ..models import BIAAnalysis, Process
from ..schemas import BIACreate, BIAOut, BIAUpdate

router = APIRouter(
    prefix="/api/bia",
    tags=["Analyse BIA"],
    dependencies=[Depends(get_current_user)],
)

writer = Depends(require_role("admin", "analyste"))


def _get_bia(db: Session, bia_id: int) -> BIAAnalysis:
    analysis = db.get(BIAAnalysis, bia_id)
    if analysis is None:
        raise HTTPException(404, "Analyse BIA introuvable")
    return analysis


@router.get("", response_model=list[BIAOut])
def list_bia(db: Session = Depends(get_db)):
    query = select(BIAAnalysis).order_by(BIAAnalysis.created_at.desc())
    return list(db.scalars(query))


# Cette route doit être déclarée avant /{bia_id}
@router.get("/process/{process_id}", response_model=BIAOut)
def get_bia_by_process(process_id: int, db: Session = Depends(get_db)):
    if db.get(Process, process_id) is None:
        raise HTTPException(404, "Processus introuvable")

    analysis = db.scalar(
        select(BIAAnalysis).where(BIAAnalysis.process_id == process_id)
    )
    if analysis is None:
        raise HTTPException(404, "Aucune analyse BIA pour ce processus")

    return analysis


@router.get("/{bia_id}", response_model=BIAOut)
def get_bia(bia_id: int, db: Session = Depends(get_db)):
    return _get_bia(db, bia_id)


@router.post("", response_model=BIAOut, status_code=201, dependencies=[writer])
def create_bia(data: BIACreate, db: Session = Depends(get_db)):
    if db.get(Process, data.process_id) is None:
        raise HTTPException(404, "Processus introuvable")

    existing = db.scalar(
        select(BIAAnalysis).where(BIAAnalysis.process_id == data.process_id)
    )
    if existing is not None:
        raise HTTPException(409, "Ce processus possède déjà une analyse BIA")

    analysis = BIAAnalysis(**data.model_dump())
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


@router.put("/{bia_id}", response_model=BIAOut, dependencies=[writer])
def update_bia(
    bia_id: int,
    data: BIAUpdate,
    db: Session = Depends(get_db),
):
    analysis = _get_bia(db, bia_id)

    for key, value in data.model_dump(exclude_unset=True).items():
        if value is None and key != "essential_resources":
            continue
        setattr(analysis, key, value)

    db.commit()
    db.refresh(analysis)
    return analysis


@router.delete(
    "/{bia_id}",
    status_code=204,
    dependencies=[Depends(require_role("admin"))],
)
def delete_bia(bia_id: int, db: Session = Depends(get_db)):
    db.delete(_get_bia(db, bia_id))
    db.commit()
