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

    # Informations existantes
    threat: Mapped[str] = mapped_column(String(200))
    vulnerability: Mapped[str] = mapped_column(String(200))
    probability: Mapped[int] = mapped_column(Integer)
    impact: Mapped[int] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer)

    # Nouveaux champs
    code: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(50))
    causes: Mapped[str | None] = mapped_column(Text)
    consequence: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(100))
    existing_measures: Mapped[str | None] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(String(80))
    review_date: Mapped[date | None] = mapped_column(Date)

    status: Mapped[str] = mapped_column(
        String(20),
        default="ouvert",
        server_default="ouvert"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now()
    )

    process = relationship("Process", back_populates="risks")
    asset = relationship("Asset", back_populates="risks")
    treatments = relationship(
        "Treatment",
        back_populates="risk",
        cascade="all, delete-orphan"
    )


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
class AuditLog(Base):
    """Journal d'audit : une ligne par action importante. Jamais modifié ni supprimé."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    username: Mapped[str] = mapped_column(String(50))  # copie du nom, garde la trace même si le compte est supprimé
    action: Mapped[str] = mapped_column(String(30), index=True)       # création | modification | suppression | connexion | échec connexion
    entity_type: Mapped[str] = mapped_column(String(30), index=True)  # risque | traitement | processus | actif | bia | utilisateur | auth
    entity_id: Mapped[int | None]
    details: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
