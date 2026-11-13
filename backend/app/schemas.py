from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from .scoring import risk_level

Role = Literal["admin", "analyste", "lecteur"]
AssetType = Literal["serveur", "application", "local", "personnel", "fournisseur"]
Scale5 = Annotated[int, Field(ge=1, le=5)]

USERNAME = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
# max 72 : limite technique de bcrypt
PASSWORD = Field(min_length=12, max_length=72)


class SetupAdmin(BaseModel):
    username: str = USERNAME
    password: str = PASSWORD


class UserCreate(BaseModel):
    username: str = USERNAME
    password: str = PASSWORD
    role: Role = "analyste"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Actifs ----------
class AssetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    asset_type: AssetType
    description: str | None = None


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    asset_type: AssetType | None = None
    description: str | None = None


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    asset_type: str
    description: str | None


# ---------- Processus (BIA) ----------
class ProcessCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    criticality: Scale5 = 3
    mtpd_hours: float | None = Field(default=None, ge=0)
    rto_hours: float | None = Field(default=None, ge=0)
    rpo_minutes: int | None = Field(default=None, ge=0)
    asset_ids: list[int] = []


class ProcessUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    criticality: Scale5 | None = None
    mtpd_hours: float | None = Field(default=None, ge=0)
    rto_hours: float | None = Field(default=None, ge=0)
    rpo_minutes: int | None = Field(default=None, ge=0)
    asset_ids: list[int] | None = None


class ProcessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None
    criticality: int
    mtpd_hours: float | None
    rto_hours: float | None
    rpo_minutes: int | None
    assets: list[AssetOut]


# ---------- Risques ----------
class RiskCreate(BaseModel):
    process_id: int
    asset_id: int | None = None
    threat: str = Field(min_length=3, max_length=200)
    vulnerability: str = Field(min_length=3, max_length=200)
    probability: Scale5
    impact: Scale5


class RiskUpdate(BaseModel):
    asset_id: int | None = None
    threat: str | None = Field(default=None, min_length=3, max_length=200)
    vulnerability: str | None = Field(default=None, min_length=3, max_length=200)
    probability: Scale5 | None = None
    impact: Scale5 | None = None


class RiskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    process_id: int
    asset_id: int | None
    threat: str
    vulnerability: str
    probability: int
    impact: int
    score: int
    created_at: datetime

    @computed_field
    @property
    def level(self) -> str:
        return risk_level(self.score)

# ---------- Traitement des risques ----------
from datetime import date

TreatmentStrategy = Literal["réduire", "accepter", "transférer", "éviter"]
TreatmentStatus = Literal["à faire", "en cours", "terminé"]


class TreatmentCreate(BaseModel):
    strategy: TreatmentStrategy
    action: str = Field(min_length=5, max_length=5000)
    owner: str | None = Field(default=None, max_length=80)
    due_date: date | None = None
    status: TreatmentStatus = "à faire"
    residual_probability: Scale5 | None = None
    residual_impact: Scale5 | None = None


class TreatmentUpdate(BaseModel):
    strategy: TreatmentStrategy | None = None
    action: str | None = Field(default=None, min_length=5, max_length=5000)
    owner: str | None = Field(default=None, max_length=80)
    due_date: date | None = None
    status: TreatmentStatus | None = None
    residual_probability: Scale5 | None = None
    residual_impact: Scale5 | None = None


class TreatmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    risk_id: int
    strategy: str
    action: str
    owner: str | None
    due_date: date | None
    status: str
    residual_probability: int | None
    residual_impact: int | None


# ---------- Analyse d'impact sur l'activité (BIA) ----------
class BIACreate(BaseModel):
    process_id: int
    financial_impact: Scale5
    operational_impact: Scale5
    legal_impact: Scale5
    reputational_impact: Scale5
    business_consequences: str = Field(min_length=10, max_length=5000)
    essential_resources: str | None = Field(default=None, max_length=5000)


class BIAUpdate(BaseModel):
    financial_impact: Scale5 | None = None
    operational_impact: Scale5 | None = None
    legal_impact: Scale5 | None = None
    reputational_impact: Scale5 | None = None
    business_consequences: str | None = Field(
        default=None, min_length=10, max_length=5000
    )
    essential_resources: str | None = Field(default=None, max_length=5000)


class BIAOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    process_id: int
    financial_impact: int
    operational_impact: int
    legal_impact: int
    reputational_impact: int
    business_consequences: str
    essential_resources: str | None
    created_at: datetime
