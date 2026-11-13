from datetime import date, datetime

from sqlalchemy import (Column, Date, DateTime, ForeignKey, Integer, String,
                        Table, Text, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# Table d'association : un processus dépend de plusieurs actifs, et inversement
process_assets = Table(
    "process_assets",
    Base.metadata,
    Column("process_id", ForeignKey("processes.id", ondelete="CASCADE"), primary_key=True),
    Column("asset_id", ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="analyste")  # admin | analyste | lecteur
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Process(Base):
    """Processus métier (ex : Paiement en ligne) avec ses exigences de continuité (BIA)."""
    __tablename__ = "processes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    criticality: Mapped[int] = mapped_column(Integer, default=3)  # 1 à 5
    mtpd_hours: Mapped[float | None]  # durée maximale d'interruption tolérable
    rto_hours: Mapped[float | None]   # temps de reprise visé
    rpo_minutes: Mapped[int | None]   # perte de données maximale tolérée

    assets = relationship("Asset", secondary=process_assets, back_populates="processes")
    risks = relationship("Risk", back_populates="process", cascade="all, delete-orphan")
    bia_analysis = relationship(
        "BIAAnalysis",
        back_populates="process",
        uselist=False,
        cascade="all, delete-orphan",
    )


class BIAAnalysis(Base):
    """Analyse d'impact sur l'activité associée à un processus."""
    __tablename__ = "bia_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(
        ForeignKey("processes.id", ondelete="CASCADE"),
        unique=True,
    )
    financial_impact: Mapped[int] = mapped_column(Integer)
    operational_impact: Mapped[int] = mapped_column(Integer)
    legal_impact: Mapped[int] = mapped_column(Integer)
    reputational_impact: Mapped[int] = mapped_column(Integer)
    business_consequences: Mapped[str] = mapped_column(Text)
    essential_resources: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    process = relationship("Process", back_populates="bia_analysis")


class Asset(Base):
    """Actif qui supporte un processus (serveur, application, local, personnel...)."""
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    asset_type: Mapped[str] = mapped_column(String(40))  # serveur, application, local, personnel, fournisseur
    description: Mapped[str | None] = mapped_column(Text)

    processes = relationship("Process", secondary=process_assets, back_populates="assets")
    risks = relationship("Risk", back_populates="asset")


class Risk(Base):
    __tablename__ = "risks"

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id", ondelete="CASCADE"))
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"))
    threat: Mapped[str] = mapped_column(String(200))         # ex : panne électrique prolongée
    vulnerability: Mapped[str] = mapped_column(String(200))  # ex : pas d'onduleur
    probability: Mapped[int] = mapped_column(Integer)        # 1 à 5
    impact: Mapped[int] = mapped_column(Integer)             # 1 à 5
    score: Mapped[int] = mapped_column(Integer)              # probability x impact
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    process = relationship("Process", back_populates="risks")
    asset = relationship("Asset", back_populates="risks")
    treatments = relationship("Treatment", back_populates="risk", cascade="all, delete-orphan")


class Treatment(Base):
    __tablename__ = "treatments"

    id: Mapped[int] = mapped_column(primary_key=True)
    risk_id: Mapped[int] = mapped_column(ForeignKey("risks.id", ondelete="CASCADE"))
    strategy: Mapped[str] = mapped_column(String(20))  # réduire | accepter | transférer | éviter
    action: Mapped[str] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(String(80))
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="à faire")  # à faire | en cours | terminé
    residual_probability: Mapped[int | None]
    residual_impact: Mapped[int | None]

    risk = relationship("Risk", back_populates="treatments")
