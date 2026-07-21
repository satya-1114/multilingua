from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HealthDto(BaseModel):
    status: str
    version: str
    checks: list[dict]


class MetricDto(BaseModel):
    metric: str
    value: float
    at: datetime


class LogEntryDto(BaseModel):
    id: str
    at: datetime
    level: str
    service: str
    message: str
