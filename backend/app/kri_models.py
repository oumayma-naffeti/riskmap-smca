from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class KRI(Base):
    """Indicateur clé de risque, rattaché à un risque."""
    __tablename__ = "kris"

    id: Mapped[int] = mapped_column(primary_key=True)
    risk_id: Mapped[int] = mapped_column(
        ForeignKey("risks.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    unit: Mapped[str | None] = mapped_column(String(20))
    threshold: Mapped[float] = mapped_column(Float)
    alert_when: Mapped[str] = mapped_column(String(20))  # au-dessus | en dessous
    owner: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class KRIMeasure(Base):
    """Une mesure d'un KRI à une date donnée."""
    __tablename__ = "kri_measures"

    id: Mapped[int] = mapped_column(primary_key=True)
    kri_id: Mapped[int] = mapped_column(
        ForeignKey("kris.id", ondelete="CASCADE"), index=True
    )
    value: Mapped[float] = mapped_column(Float)
    measured_at: Mapped[date] = mapped_column(Date)
    comment: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
