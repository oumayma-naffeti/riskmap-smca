from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AlertWhen = Literal["au-dessus", "en dessous"]


class KRICreate(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    unit: str | None = Field(default=None, max_length=20)
    threshold: float
    alert_when: AlertWhen
    owner: str | None = Field(default=None, max_length=80)
    description: str | None = None


class KRIUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=200)
    unit: str | None = Field(default=None, max_length=20)
    threshold: float | None = None
    alert_when: AlertWhen | None = None
    owner: str | None = Field(default=None, max_length=80)
    description: str | None = None


class KRIOut(BaseModel):
    id: int
    risk_id: int
    name: str
    unit: str | None
    threshold: float
    alert_when: str
    owner: str | None
    description: str | None
    last_value: float | None
    last_measured_at: date | None
    state: str  # sans mesure | normal | alerte


class MeasureCreate(BaseModel):
    value: float
    measured_at: date | None = None
    comment: str | None = Field(default=None, max_length=300)


class MeasureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kri_id: int
    value: float
    measured_at: date
    comment: str | None
    created_at: datetime
