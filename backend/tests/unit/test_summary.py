"""Unit tests for SummaryService."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.summary import SummaryResponse
from app.services.summary import SummaryService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DOCUMENT_ID = uuid.uuid4()
_CHUNK_ID = uuid.uuid4()

_VALID_SUMMARY_JSON = json.dumps(
    {
        "obligations": [
            {"text": "Must file quarterly reports.", "page_number": 1, "chunk_id": None}
        ],
        "risks": [
            {
                "text": "Failure to file results in fines.",
                "severity": "high",
                "page_number": 2,
                "chunk_id": None,
            }
        ],
        "gaps": [
            {
                "text": "No data retention policy found.",
                "page_number": None,
                "chunk_id": None,
            }
        ],
        "recommendations": [
            {"text": "Implement a data retention policy.", "priority": "medium"}
        ],
    }
)

_VALID_MAP_JSON = json.dumps(
    {
        "obligations": ["Must file quarterly reports."],
        "risks": ["Failure to file results in fines."],
        "gaps": ["No data retention policy found."],
        "recommendations": ["Implement a data retention policy."],
    }
)


def _make_chunk(index: int = 0) -> MagicMock:
    c = MagicMock()
    c.id = uuid.uuid4()
    c.chunk_index = index
    c.page_number = index + 1
    c.text = f"Chunk text for index {index}."
    return c


def _make_summary_row() -> MagicMock:
    row = MagicMock()
    row.document_id = _DOCUMENT_ID
    row.obligations = [
        {"text": "Must file quarterly reports.", "page_number": 1, "chunk_id": None}
    ]
    row.risks = [
        {
            "text": "Failure to file results in fines.",
            "severity": "high",
            "page_number": 2,
            "chunk_id": None,
        }
    ]
    row.gaps = [
        {
            "text": "No data retention policy found.",
            "page_number": None,
            "chunk_id": None,
        }
    ]
    row.recommendations = [
        {"text": "Implement a data retention policy.", "priority": "medium"}
    ]
    row.generated_at = datetime.now(UTC)
    return row


def _make_session(
    *,
    cached_summary: Any = None,  # noqa: ANN401
    chunks: list[Any] | None = None,  # noqa: ANN401
) -> MagicMock:
    """Build a mock AsyncSession with controllable execute() results."""
    call_count = 0

    async def _execute(stmt: object, params: object = None) -> MagicMock:  # noqa: ANN001
        nonlocal call_count
        result = MagicMock()
        if call_count == 0:
            # First call: Summary cache lookup
            result.scalar_one_or_none.return_value = cached_summary
        else:
            # Second call: Chunk fetch
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = chunks or []
            result.scalars.return_value = scalars_mock
        call_count += 1
        return result

    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock(side_effect=_execute)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_returns_cached_summary_when_exists() -> None:
    """When a Summary row already exists, return it with cached=True; no LLM calls."""
    cached_row = _make_summary_row()
    session = _make_session(cached_summary=cached_row)

    with patch("app.services.summary._call_summary_llm") as mock_llm:
        svc = SummaryService(session)
        result = await svc.get_or_generate(_DOCUMENT_ID)

    assert isinstance(result, SummaryResponse)
    assert result.cached is True
    assert result.document_id == _DOCUMENT_ID
    assert len(result.obligations) == 1
    mock_llm.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_generates_summary_direct_strategy() -> None:
    """≤30 chunks → single LLM call, cached=False, fields populated."""
    chunks = [_make_chunk(i) for i in range(5)]
    session = _make_session(cached_summary=None, chunks=chunks)

    with patch(
        "app.services.summary._call_summary_llm", new_callable=AsyncMock
    ) as mock_llm:
        mock_llm.return_value = _VALID_SUMMARY_JSON

        svc = SummaryService(session)
        result = await svc.get_or_generate(_DOCUMENT_ID)

    assert result.cached is False
    assert len(result.obligations) == 1
    assert result.obligations[0].text == "Must file quarterly reports."
    assert len(result.risks) == 1
    assert result.risks[0].severity.value == "high"
    assert len(result.gaps) == 1
    assert len(result.recommendations) == 1
    assert result.recommendations[0].priority.value == "medium"

    # One call for direct strategy
    mock_llm.assert_called_once()
    call_kwargs = mock_llm.call_args.kwargs
    assert call_kwargs["strategy"] == "direct"
    assert call_kwargs["chunk_count"] == 5

    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_generates_summary_map_reduce_strategy() -> None:
    """35 chunks → map_reduce: 4 map calls (batches of 10) + 1 reduce call."""
    chunks = [_make_chunk(i) for i in range(35)]
    session = _make_session(cached_summary=None, chunks=chunks)

    with (
        patch(
            "app.services.summary._call_summary_llm", new_callable=AsyncMock
        ) as mock_reduce,
        patch("app.services.summary._call_map_llm", new_callable=AsyncMock) as mock_map,
    ):
        mock_map.return_value = _VALID_MAP_JSON
        mock_reduce.return_value = _VALID_SUMMARY_JSON

        svc = SummaryService(session)
        result = await svc.get_or_generate(_DOCUMENT_ID)

    # 35 chunks / 10 per batch = 4 batches (10+10+10+5)
    assert mock_map.call_count == 4
    # 1 reduce call
    assert mock_reduce.call_count == 1
    reduce_kwargs = mock_reduce.call_args.kwargs
    assert reduce_kwargs["strategy"] == "map_reduce"

    assert result.cached is False
    assert len(result.obligations) == 1
    session.commit.assert_called_once()
