"""Unit tests for RetrievalService."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.retrieval import RetrievalService


def _make_row(
    chunk_id: uuid.UUID,
    text: str,
    page_number: int | None,
    similarity: float,
) -> MagicMock:
    row = MagicMock()
    row.id = str(chunk_id)
    row.text = text
    row.page_number = page_number
    row.similarity = similarity
    return row


def _make_db_session(rows: list[MagicMock]) -> MagicMock:
    result = MagicMock()
    result.fetchall.return_value = rows

    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_retrieve_returns_chunks_ordered_by_similarity() -> None:
    """Rows returned by SQL are already ordered; service preserves that order."""
    doc_id = uuid.uuid4()
    ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    rows = [
        _make_row(ids[0], "Most relevant", 1, 0.95),
        _make_row(ids[1], "Second best", 2, 0.75),
        _make_row(ids[2], "Third best", None, 0.55),
    ]
    db = _make_db_session(rows)

    fake_embedding = [0.1] * 1536
    mock_provider = MagicMock()
    mock_provider.embed = AsyncMock(return_value=[fake_embedding])

    with patch(
        "app.services.retrieval.get_embedding_provider", return_value=mock_provider
    ):
        svc = RetrievalService(db)
        result = await svc.retrieve("some query", doc_id, top_k=5)

    assert len(result) == 3
    assert result[0].chunk_id == ids[0]
    assert result[0].similarity == pytest.approx(0.95)
    assert result[1].chunk_id == ids[1]
    assert result[2].chunk_id == ids[2]
    assert result[2].page_number is None


@pytest.mark.asyncio
async def test_retrieve_filters_low_similarity() -> None:
    """Chunks with similarity < 0.3 must be excluded."""
    doc_id = uuid.uuid4()
    high_id = uuid.uuid4()
    low_id = uuid.uuid4()
    rows = [
        _make_row(high_id, "Good chunk", 1, 0.8),
        _make_row(low_id, "Poor chunk", 2, 0.1),
    ]
    db = _make_db_session(rows)

    fake_embedding = [0.1] * 1536
    mock_provider = MagicMock()
    mock_provider.embed = AsyncMock(return_value=[fake_embedding])

    with patch(
        "app.services.retrieval.get_embedding_provider", return_value=mock_provider
    ):
        svc = RetrievalService(db)
        result = await svc.retrieve("query", doc_id)

    chunk_ids = {r.chunk_id for r in result}
    assert high_id in chunk_ids
    assert low_id not in chunk_ids


@pytest.mark.asyncio
async def test_retrieve_exactly_at_threshold_excluded() -> None:
    """Similarity exactly equal to 0.3 is below the strict threshold and excluded."""
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    rows = [_make_row(chunk_id, "Borderline chunk", 1, 0.29)]
    db = _make_db_session(rows)

    mock_provider = MagicMock()
    mock_provider.embed = AsyncMock(return_value=[[0.0] * 1536])

    with patch(
        "app.services.retrieval.get_embedding_provider", return_value=mock_provider
    ):
        svc = RetrievalService(db)
        result = await svc.retrieve("query", doc_id)

    assert result == []


@pytest.mark.asyncio
async def test_retrieve_scoped_to_document_id() -> None:
    """The document_id is passed through to the SQL query."""
    doc_id = uuid.uuid4()
    db = _make_db_session([])
    mock_provider = MagicMock()
    mock_provider.embed = AsyncMock(return_value=[[0.0] * 1536])

    with patch(
        "app.services.retrieval.get_embedding_provider", return_value=mock_provider
    ):
        svc = RetrievalService(db)
        await svc.retrieve("query", doc_id, top_k=3)

    call_kwargs = db.execute.call_args
    # Second positional arg is the params dict
    params = call_kwargs[0][1]
    assert params["document_id"] == str(doc_id)
    assert params["top_k"] == 3


@pytest.mark.asyncio
async def test_retrieve_calls_embed_once_with_query() -> None:
    """embed() is called exactly once with the query string."""
    doc_id = uuid.uuid4()
    db = _make_db_session([])
    mock_provider = MagicMock()
    mock_provider.embed = AsyncMock(return_value=[[0.5] * 1536])

    with patch(
        "app.services.retrieval.get_embedding_provider", return_value=mock_provider
    ):
        svc = RetrievalService(db)
        await svc.retrieve("test query", doc_id)

    mock_provider.embed.assert_called_once_with(["test query"])
