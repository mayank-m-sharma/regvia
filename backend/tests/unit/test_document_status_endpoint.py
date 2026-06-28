"""Unit tests for GET /api/v1/documents/{id}."""

import uuid
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.db.session import get_db
from app.main import app


@pytest.fixture()
def override_db_no_doc() -> Generator[None, None, None]:
    """Override get_db to return no document (simulates unknown ID)."""

    async def _execute(stmt: object) -> MagicMock:  # noqa: ANN001
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        return result

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=_execute)

    async def _mock_get_db() -> AsyncGenerator[MagicMock, None]:
        yield mock_db

    app.dependency_overrides[get_db] = _mock_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_get_unknown_document_returns_404(
    async_client: AsyncClient,
    override_auth: None,
    override_db_no_doc: None,
) -> None:
    response = await async_client.get(f"/api/v1/documents/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"
