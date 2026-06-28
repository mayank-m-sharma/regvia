"""Unit tests for REGVIA-030 knowledge library endpoints."""

import io
import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.auth import get_current_user
from app.db.session import get_db
from app.main import app
from app.models.user import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_USER_ID = uuid.uuid4()
_DOC_ID = uuid.uuid4()


def _make_stub_user() -> MagicMock:
    user = MagicMock(spec=User)
    user.id = _USER_ID
    user.email = "test@example.com"
    return user


def _make_doc(
    in_library: bool = False,
    content_hash: str | None = None,
) -> MagicMock:
    doc = MagicMock()
    doc.id = _DOC_ID
    doc.filename = "policy.pdf"
    doc.s3_key = f"documents/{_DOC_ID}/policy.pdf"
    doc.size_bytes = 1024
    doc.status = "pending"
    doc.chunk_count = None
    doc.in_library = in_library
    doc.content_hash = content_hash
    doc.owner_id = _USER_ID
    doc.created_at = datetime.now(UTC)
    doc.updated_at = datetime.now(UTC)
    return doc


@pytest.fixture()
def override_auth_user() -> Generator[MagicMock, None, None]:
    stub = _make_stub_user()

    async def _mock() -> MagicMock:
        return stub

    app.dependency_overrides[get_current_user] = _mock
    yield stub
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# GET /api/v1/documents  — list user documents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_documents_returns_owned_docs(
    async_client: AsyncClient,
    override_auth_user: MagicMock,
) -> None:
    doc = _make_doc(in_library=True)

    async def _execute(stmt: object) -> MagicMock:  # noqa: ANN001
        result = MagicMock()
        result.scalars.return_value.all.return_value = [doc]
        return result

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=_execute)

    async def _mock_db() -> AsyncGenerator[MagicMock, None]:
        yield mock_db

    app.dependency_overrides[get_db] = _mock_db
    try:
        response = await async_client.get("/api/v1/documents")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["filename"] == "policy.pdf"
    assert data[0]["in_library"] is True


@pytest.mark.asyncio
async def test_list_documents_empty(
    async_client: AsyncClient,
    override_auth_user: MagicMock,
) -> None:
    async def _execute(stmt: object) -> MagicMock:  # noqa: ANN001
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        return result

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=_execute)

    async def _mock_db() -> AsyncGenerator[MagicMock, None]:
        yield mock_db

    app.dependency_overrides[get_db] = _mock_db
    try:
        response = await async_client.get("/api/v1/documents")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json()["data"] == []


# ---------------------------------------------------------------------------
# PATCH /api/v1/documents/{id}/library  — add to library
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_to_library_sets_in_library_true(
    async_client: AsyncClient,
    override_auth_user: MagicMock,
) -> None:
    doc = _make_doc(in_library=False)

    async def _execute(stmt: object) -> MagicMock:  # noqa: ANN001
        result = MagicMock()
        result.scalar_one_or_none.return_value = doc
        return result

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=_execute)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(
        side_effect=lambda obj: setattr(obj, "in_library", True)
    )  # noqa: B023

    async def _mock_db() -> AsyncGenerator[MagicMock, None]:
        yield mock_db

    app.dependency_overrides[get_db] = _mock_db
    try:
        response = await async_client.patch(f"/api/v1/documents/{_DOC_ID}/library")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json()["data"]["in_library"] is True


@pytest.mark.asyncio
async def test_add_to_library_404_for_unknown(
    async_client: AsyncClient,
    override_auth_user: MagicMock,
) -> None:
    async def _execute(stmt: object) -> MagicMock:  # noqa: ANN001
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        return result

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=_execute)

    async def _mock_db() -> AsyncGenerator[MagicMock, None]:
        yield mock_db

    app.dependency_overrides[get_db] = _mock_db
    try:
        response = await async_client.patch(f"/api/v1/documents/{uuid.uuid4()}/library")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /documents  — duplicate detection returns existing doc
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_returns_existing_on_duplicate(
    async_client: AsyncClient,
    override_auth_user: MagicMock,
) -> None:
    existing = _make_doc(in_library=False, content_hash="abc123")

    async def _execute(stmt: object) -> MagicMock:  # noqa: ANN001
        result = MagicMock()
        result.scalar_one_or_none.return_value = existing
        return result

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=_execute)

    async def _mock_db() -> AsyncGenerator[MagicMock, None]:
        yield mock_db

    app.dependency_overrides[get_db] = _mock_db
    try:
        with patch("app.api.v1.documents.storage_client"):
            response = await async_client.post(
                "/api/v1/documents",
                files={
                    "file": (
                        "policy.pdf",
                        io.BytesIO(b"%PDF-1.4 content"),
                        "application/pdf",
                    )
                },
            )
    finally:
        app.dependency_overrides.pop(get_db, None)

    # Returns 202 with existing document — no re-upload
    assert response.status_code == 202
    data = response.json()["data"]
    assert data["document_id"] == str(_DOC_ID)
    assert data["in_library"] is False


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_library_endpoints_require_auth(async_client: AsyncClient) -> None:
    r1 = await async_client.get("/api/v1/documents")
    r2 = await async_client.patch(f"/api/v1/documents/{uuid.uuid4()}/library")
    assert r1.status_code == 401
    assert r2.status_code == 401
