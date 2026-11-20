"""Écriture dans le journal d'audit."""
from sqlalchemy.orm import Session

from .models import AuditLog, User


def log_action(db: Session, user: User | None, action: str, entity_type: str,
               entity_id: int | None = None, details: str | None = None) -> None:
    """Ajoute une ligne d'audit SANS valider la transaction.

    Le commit est fait par la route : l'action et sa trace sont enregistrées
    ensemble, ou pas du tout.
    """
    db.add(AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else "anonyme",
        action=action, entity_type=entity_type,
        entity_id=entity_id, details=details,
    ))


def describe_changes(obj, changes: dict) -> str:
    """Compare l'objet AVANT modification avec les nouvelles valeurs.

    Exemple : "probability: 3 → 4; impact: 2 → 5"
    À appeler avant les setattr, sinon l'ancienne valeur est déjà perdue.
    """
    parts = [f"{key}: {getattr(obj, key, None)} → {new}"
             for key, new in changes.items() if getattr(obj, key, None) != new]
    return "; ".join(parts) or "aucun changement"
