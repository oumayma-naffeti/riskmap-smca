from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_role
from ..models import AuditLog
from ..schemas import AuditLogOut

# Lecture seule, réservée à l'admin. Aucune route PUT/DELETE : le journal ne se modifie pas.
router = APIRouter(prefix="/api/audit-logs", tags=["Audit"],
                   dependencies=[Depends(require_role("admin"))])


@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(entity_type: str | None = None, action: str | None = None,
                    username: str | None = None,
                    limit: int = Query(100, ge=1, le=500),
                    db: Session = Depends(get_db)):
    query = select(AuditLog).order_by(AuditLog.id.desc())
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if action:
        query = query.where(AuditLog.action == action)
    if username:
        query = query.where(AuditLog.username == username)
    return db.scalars(query.limit(limit)).all()
