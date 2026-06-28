"""Unit tests for JWT creation and verification (app.core.auth)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from jose import jwt

from app.core.auth import create_access_token, decode_access_token
from app.core.settings import settings


def test_create_access_token_returns_string() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_access_token_contains_correct_sub() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    payload = jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    assert payload["sub"] == str(user_id)


def test_create_access_token_contains_expiry() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    payload = jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    assert "exp" in payload
    exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
    assert exp > datetime.now(UTC)


def test_decode_valid_token_returns_user_id() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    result = decode_access_token(token)
    assert result == user_id


def test_decode_expired_token_raises_401() -> None:
    user_id = uuid.uuid4()
    # Create a token that expired 1 second ago
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(UTC) - timedelta(seconds=1),
    }
    expired_token = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(expired_token)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "UNAUTHORIZED"  # type: ignore[index]


def test_decode_tampered_token_raises_401() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    # Tamper by appending a character
    tampered = token + "x"
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(tampered)
    assert exc_info.value.status_code == 401


def test_decode_wrong_secret_raises_401() -> None:
    user_id = uuid.uuid4()
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    token = jwt.encode(payload, "wrong-secret", algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)
    assert exc_info.value.status_code == 401


def test_decode_token_missing_sub_raises_401() -> None:
    payload = {"exp": datetime.now(UTC) + timedelta(hours=1)}
    token = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)
    assert exc_info.value.status_code == 401
