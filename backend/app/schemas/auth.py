"""Pydantic schemas for auth endpoints."""

import uuid

from pydantic import BaseModel


class LoginUrlResponse(BaseModel):
    url: str
    state: str  # frontend stores this in sessionStorage to validate on callback


class ExchangeRequest(BaseModel):
    code: str


class ExchangeResponse(BaseModel):
    token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    avatar_url: str | None

    model_config = {"from_attributes": True}
