"""Schemas for the compliance summary endpoint."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from pydantic import BaseModel


class SeverityLevel(enum.StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


class Obligation(BaseModel):
    text: str
    page_number: int | None
    chunk_id: uuid.UUID | None


class Risk(BaseModel):
    text: str
    severity: SeverityLevel
    page_number: int | None
    chunk_id: uuid.UUID | None


class Gap(BaseModel):
    text: str
    page_number: int | None
    chunk_id: uuid.UUID | None


class Recommendation(BaseModel):
    text: str
    priority: SeverityLevel


class SummaryResponse(BaseModel):
    document_id: uuid.UUID
    obligations: list[Obligation]
    risks: list[Risk]
    gaps: list[Gap]
    recommendations: list[Recommendation]
    generated_at: datetime
    cached: bool  # true if returned from DB cache
