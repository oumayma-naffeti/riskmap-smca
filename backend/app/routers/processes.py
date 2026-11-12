from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_role
from ..models import Asset, Process
from ..schemas import ProcessCreate, ProcessOut, ProcessUpdate

router = APIRouter(prefix="/api/processes", tags=["Processus"],
                   dependencies=[Depends(get_current_user)])
writer = Depends(require_role("admin", "analyste"))
NULLABLE = {"description", "mtpd_hours", "rto_hours", "rpo_minutes"}


def _get(db: Session, process_id: int) -> Process:
    process = db.get(Process, process_id)
    if process is None:
        raise HTTPException(404, "Processus introuvable")
    return process


def _assets(db: Session, ids: list[int]) -> list[Asset]:
    ids = set(ids)
    if not ids:
        return []
    found = list(db.scalars(select(Asset).where(Asset.id.in_(ids))))
    if len(found) != len(ids):
        raise HTTPException(404, "Un ou plusieurs actifs sont introuvables")
    return found


def _name_free(db: Session, name: str, exclude_id: int | None = None) -> None:
    other = db.scalar(select(Process).where(Process.name == name))
    if other and other.id != exclude_id:
        raise HTTPException(409, "Un processus porte déjà ce nom")


def _check_bia(rto: float | None, mtpd: float | None) -> None:
    # ISO 22301 : la reprise visée (RTO) doit tenir dans l'interruption tolérable (MTPD)
    if rto is not None and mtpd is not None and rto > mtpd:
        raise HTTPException(422, "Le RTO doit être inférieur ou égal au MTPD")


@router.get("", response_model=list[ProcessOut])
def list_processes(db: Session = Depends(get_db)):
    query = select(Process).order_by(Process.criticality.desc(), Process.name)
    return [ProcessOut.model_validate(p) for p in db.scalars(query)]


@router.get("/{process_id}", response_model=ProcessOut)
def get_process(process_id: int, db: Session = Depends(get_db)):
    return ProcessOut.model_validate(_get(db, process_id))


@router.post("", response_model=ProcessOut, status_code=201, dependencies=[writer])
def create_process(data: ProcessCreate, db: Session = Depends(get_db)):
    _name_free(db, data.name)
    _check_bia(data.rto_hours, data.mtpd_hours)
    process = Process(**data.model_dump(exclude={"asset_ids"}))
    process.assets = _assets(db, data.asset_ids)
    db.add(process)
    db.commit()
    db.refresh(process)
    return ProcessOut.model_validate(process)


@router.put("/{process_id}", response_model=ProcessOut, dependencies=[writer])
def update_process(process_id: int, data: ProcessUpdate, db: Session = Depends(get_db)):
    process = _get(db, process_id)
    fields = data.model_dump(exclude_unset=True)
    asset_ids = fields.pop("asset_ids", None)
    for key, value in fields.items():
        if value is None and key not in NULLABLE:
            continue
        if key == "name":
            _name_free(db, value, process.id)
        setattr(process, key, value)
    _check_bia(process.rto_hours, process.mtpd_hours)
    if asset_ids is not None:
        process.assets = _assets(db, asset_ids)
    db.commit()
    db.refresh(process)
    return ProcessOut.model_validate(process)


@router.delete("/{process_id}", status_code=204, dependencies=[Depends(require_role("admin"))])
def delete_process(process_id: int, db: Session = Depends(get_db)):
    db.delete(_get(db, process_id))  # supprime aussi ses risques (cascade)
    db.commit()
