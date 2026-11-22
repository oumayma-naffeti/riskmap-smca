from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ControlType = Literal["préventif", "détectif", "correctif"]
Effectiveness = Literal["non évaluée", "faible", "moyenne", "élevée"]


def _check_dates(last, nxt):
    if last and nxt and nxt < last:
        raise ValueError("La date du prochain test précède celle du dernier test")


class ControlCreate(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    control_type: ControlType
    effectiveness: Effectiveness = "non évaluée"
    owner: str | None = Field(default=None, max_length=80)
    description: str | None = None
    last_test_date: date | None = None
    next_test_date: date | None = None

    @model_validator(mode="after")
    def dates_ok(self):
        _check_dates(self.last_test_date, self.next_test_date)
        return self


class ControlUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=200)
    control_type: ControlType | None = None
    effectiveness: Effectiveness | None = None
    owner: str | None = Field(default=None, max_length=80)
    description: str | None = None
    last_test_date: date | None = None
    next_test_date: date | None = None


class ControlOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    risk_id: int
    name: str
    control_type: str
    effectiveness: str
    owner: str | None
    description: str | None
    last_test_date: date | None
    next_test_date: date | None
    created_at: datetime
