"""Unit tests for POST /api/v1/documents/{document_id}/summary."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.db.session import get_db
from app.main import app
from app.schemas.summary import (
    Gap,
    Obligation,
    Recommendation,
    Risk,
    SeverityLevel,
    SummaryResponse,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DOCUMENT_ID = uuid.uuid4()
_UNKNOWN_ID = uuid.uuid4()

# ---------------------------------------------------------------------------
# Mock DB helpers
# ---------------------------------------------------------------------------


def _make_ready_doc() -> MagicMock:
    from app.models.document import DocumentStatus

    doc = MagicMock()
    doc.id = _DOCUMENT_ID
    doc.status = DocumentStatus.ready
    return doc


def _make_pending_doc() -> MagicMock:
    from app.models.document import DocumentStatus

    doc = MagicMock()
    doc.id = _DOCUMENT_ID
    doc.status = DocumentStatus.pending
    return doc


def _make_db_returning(doc: MagicMock | None) -> MagicMock:
    async def _execute(stmt: object, params: object = None) -> MagicMock:  # noqa: ANN001
        result = MagicMock()
        result.scalar_one_or_none.return_value = doc
        return result

    session = MagicMock()
    session.execute = AsyncMock(side_effect=_execute)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def override_db_not_found() -> Generator[None, None, None]:
    """DB returns None for every lookup → document not found."""

    async def _mock_db() -> AsyncGenerator[MagicMock, None]:
        yield _make_db_returning(None)

    app.dependency_overrides[get_db] = _mock_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def override_db_not_ready() -> Generator[None, None, None]:
    """DB returns a pending document → not ready."""

    async def _mock_db() -> AsyncGenerator[MagicMock, None]:
        yield _make_db_returning(_make_pending_doc())

    app.dependency_overrides[get_db] = _mock_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def override_db_ready() -> Generator[None, None, None]:
    """DB returns a ready document."""

    async def _mock_db() -> AsyncGenerator[MagicMock, None]:
        yield _make_db_returning(_make_ready_doc())

    app.dependency_overrides[get_db] = _mock_db
    yield
    app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Sample response
# ---------------------------------------------------------------------------


def _sample_summary() -> SummaryResponse:
    return SummaryResponse(
        document_id=_DOCUMENT_ID,
        obligations=[
            Obligation(
                text="Must file quarterly reports.", page_number=1, chunk_id=None
            )
        ],
        risks=[
            Risk(
                text="Failure to file results in fines.",
                severity=SeverityLevel.high,
                page_number=2,
                chunk_id=None,
            )
        ],
        gaps=[
            Gap(text="No data retention policy found.", page_number=None, chunk_id=None)
        ],
        recommendations=[
            Recommendation(
                text="Implement a data retention policy.", priority=SeverityLevel.medium
            )
        ],
        generated_at=datetime.now(UTC),
        cached=False,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_endpoint_returns_404_for_unknown_document(
    async_client: AsyncClient,
    override_db_not_found: None,
    override_auth: None,
) -> None:
    response = await async_client.post(
        f"/api/v1/documents/{_UNKNOWN_ID}/summary",
    )
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "DOCUMENT_NOT_FOUND"


@pytest.mark.asyncio
async def test_endpoint_returns_422_for_unready_document(
    async_client: AsyncClient,
    override_db_not_ready: None,
    override_auth: None,
) -> None:
    response = await async_client.post(
        f"/api/v1/documents/{_DOCUMENT_ID}/summary",
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "DOCUMENT_NOT_READY"


@pytest.mark.asyncio
async def test_endpoint_returns_202_with_summary(
    async_client: AsyncClient,
    override_db_ready: None,
    override_auth: None,
) -> None:
    sample = _sample_summary()

    with patch(
        "app.api.v1.documents.SummaryService",
    ) as mock_svc_cls:
        mock_svc = MagicMock()
        mock_svc.get_or_generate = AsyncMock(return_value=sample)
        mock_svc_cls.return_value = mock_svc

        response = await async_client.post(
            f"/api/v1/documents/{_DOCUMENT_ID}/summary",
        )

    assert response.status_code == 202
    body = response.json()
    assert body["error"] is None
    data = body["data"]
    assert data["document_id"] == str(_DOCUMENT_ID)
    assert data["cached"] is False
    assert len(data["obligations"]) == 1
    assert data["obligations"][0]["text"] == "Must file quarterly reports."
    assert len(data["risks"]) == 1
    assert data["risks"][0]["severity"] == "high"
    assert len(data["gaps"]) == 1
    assert len(data["recommendations"]) == 1
    assert data["recommendations"][0]["priority"] == "medium"
