from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Control(Base):
    """Contrôle (mesure de maîtrise) rattaché à un risque."""
    __tablename__ = "controls"

    id: Mapped[int] = mapped_column(primary_key=True)
    risk_id: Mapped[int] = mapped_column(
        ForeignKey("risks.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    control_type: Mapped[str] = mapped_column(String(20))  # préventif | détectif | correctif
    effectiveness: Mapped[str] = mapped_column(
        String(20), default="non évaluée", server_default="non évaluée"
    )
    owner: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)
    last_test_date: Mapped[date | None] = mapped_column(Date)
    next_test_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
