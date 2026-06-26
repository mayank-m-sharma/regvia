"""Unit tests for the upload endpoint — S3 and DB are mocked."""

import io
import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.db.session import get_db
from app.main import app


def _make_mock_db() -> MagicMock:
    """Return a mock AsyncSession that satisfies the DB dependency."""
    mock_session = MagicMock()

    # refresh() must be awaitable and set the id/timestamps on the doc
    async def _refresh(obj: object) -> None:
        obj_dict = obj.__dict__
        if "id" not in obj_dict or obj_dict["id"] is None:
            object.__setattr__(obj, "id", uuid.uuid4())
        if "created_at" not in obj_dict or obj_dict["created_at"] is None:
            object.__setattr__(obj, "created_at", datetime.now(UTC))
        if "updated_at" not in obj_dict or obj_dict["updated_at"] is None:
            object.__setattr__(obj, "updated_at", datetime.now(UTC))

    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock(side_effect=_refresh)
    return mock_session


@pytest.fixture()
def override_db() -> Generator[None, None, None]:
    """Override the get_db dependency with a mock session."""

    async def _mock_get_db() -> AsyncGenerator[MagicMock, None]:
        yield _make_mock_db()

    app.dependency_overrides[get_db] = _mock_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_upload_rejects_non_pdf(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/documents",
        files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file(async_client: AsyncClient) -> None:
    big = io.BytesIO(b"x" * (52_428_801))
    with patch("app.api.v1.documents.storage_client") as mock_storage:
        mock_storage.upload = AsyncMock()
        response = await async_client.post(
            "/api/v1/documents",
            files={"file": ("test.pdf", big, "application/pdf")},
        )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_upload_valid_pdf_returns_202(
    async_client: AsyncClient,
    override_db: None,
) -> None:
    pdf_content = b"%PDF-1.4 test content"
    with (
        patch("app.api.v1.documents.storage_client") as mock_storage,
        patch("app.api.v1.documents.process_document"),
    ):
        mock_storage.upload = AsyncMock()
        response = await async_client.post(
            "/api/v1/documents",
            files={"file": ("policy.pdf", io.BytesIO(pdf_content), "application/pdf")},
        )
    assert response.status_code == 202
    data = response.json()["data"]
    assert data["status"] == "pending"
    assert data["filename"] == "policy.pdf"
    assert "document_id" in data
