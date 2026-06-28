"""Unit tests for POST /api/v1/chat/stream (SSE)."""

import uuid
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.db.session import get_db
from app.main import app
from app.services.retrieval import RetrievedChunk

_DOCUMENT_ID = uuid.uuid4()
_CHUNK_ID = uuid.uuid4()


def _make_ready_document() -> MagicMock:
    doc = MagicMock()
    doc.id = _DOCUMENT_ID
    doc.status = "ready"
    return doc


def _make_chat_session() -> MagicMock:
    sess = MagicMock()
    sess.id = uuid.uuid4()
    return sess


def _make_mock_db(doc: MagicMock | None = None) -> MagicMock:
    if doc is None:
        doc = _make_ready_document()
    call_count = 0

    async def _execute(stmt: object, params: object = None) -> MagicMock:  # noqa: ANN001
        nonlocal call_count
        result = MagicMock()
        if call_count == 0:
            result.scalar_one_or_none.return_value = doc
        else:
            result.scalar_one_or_none.return_value = None
        call_count += 1
        return result

    _pending: list[object] = []

    def _add(obj: object) -> None:
        _pending.append(obj)
        if not hasattr(obj, "id") or getattr(obj, "id", None) is None:
            object.__setattr__(obj, "id", uuid.uuid4())

    async def _flush() -> None:
        for obj in _pending:
            if not hasattr(obj, "id") or getattr(obj, "id", None) is None:
                object.__setattr__(obj, "id", uuid.uuid4())

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(side_effect=_execute)
    mock_session.add = MagicMock(side_effect=_add)
    mock_session.flush = AsyncMock(side_effect=_flush)
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    return mock_session


@pytest.fixture()
def override_db_stream() -> Generator[None, None, None]:
    async def _mock_get_db() -> AsyncGenerator[MagicMock, None]:
        yield _make_mock_db()

    app.dependency_overrides[get_db] = _mock_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


def _sample_chunks() -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            chunk_id=_CHUNK_ID,
            text="Compliance requires timely reporting.",
            page_number=5,
            similarity=0.88,
        )
    ]


def _parse_sse(raw: str) -> list[dict[str, str]]:
    """Parse raw SSE text into list of {event, data} dicts."""

    events: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in raw.splitlines():
        if line.startswith("event: "):
            current["event"] = line[len("event: ") :]
        elif line.startswith("data: "):
            current["data"] = line[len("data: ") :]
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events


async def _make_async_gen(*values: str) -> AsyncGenerator[str, None]:
    for v in values:
        yield v


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_returns_event_stream_content_type(
    async_client: AsyncClient,
    override_db_stream: None,
    override_auth: None,
) -> None:
    async def _fake_stream(**kwargs: object) -> AsyncGenerator[str, None]:
        yield "Hello"

    with (
        patch("app.api.v1.chat.RetrievalService") as mock_svc_cls,
        patch("app.api.v1.chat._call_llm_stream") as mock_stream,
    ):
        mock_svc = MagicMock()
        mock_svc.retrieve = AsyncMock(return_value=_sample_chunks())
        mock_svc_cls.return_value = mock_svc
        mock_stream.return_value = _fake_stream()

        response = await async_client.post(
            "/api/v1/chat/stream",
            json={
                "document_id": str(_DOCUMENT_ID),
                "question": "What is required?",
            },
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_stream_emits_token_events(
    async_client: AsyncClient,
    override_db_stream: None,
    override_auth: None,
) -> None:
    async def _fake_stream(**kwargs: object) -> AsyncGenerator[str, None]:
        yield "Hello"
        yield " world"

    with (
        patch("app.api.v1.chat.RetrievalService") as mock_svc_cls,
        patch("app.api.v1.chat._call_llm_stream") as mock_stream,
    ):
        mock_svc = MagicMock()
        mock_svc.retrieve = AsyncMock(return_value=[])
        mock_svc_cls.return_value = mock_svc
        mock_stream.return_value = _fake_stream()

        response = await async_client.post(
            "/api/v1/chat/stream",
            json={
                "document_id": str(_DOCUMENT_ID),
                "question": "Tokens?",
            },
        )

    events = _parse_sse(response.text)
    token_events = [e for e in events if e.get("event") == "token"]
    assert len(token_events) == 2
    import json

    assert json.loads(token_events[0]["data"])["token"] == "Hello"
    assert json.loads(token_events[1]["data"])["token"] == " world"


@pytest.mark.asyncio
async def test_stream_emits_citations_event(
    async_client: AsyncClient,
    override_db_stream: None,
    override_auth: None,
) -> None:
    async def _fake_stream(**kwargs: object) -> AsyncGenerator[str, None]:
        yield f"Timely reporting is required. [chunk:{_CHUNK_ID}]"

    with (
        patch("app.api.v1.chat.RetrievalService") as mock_svc_cls,
        patch("app.api.v1.chat._call_llm_stream") as mock_stream,
    ):
        mock_svc = MagicMock()
        mock_svc.retrieve = AsyncMock(return_value=_sample_chunks())
        mock_svc_cls.return_value = mock_svc
        mock_stream.return_value = _fake_stream()

        response = await async_client.post(
            "/api/v1/chat/stream",
            json={
                "document_id": str(_DOCUMENT_ID),
                "question": "What is required?",
            },
        )

    import json

    events = _parse_sse(response.text)
    citation_events = [e for e in events if e.get("event") == "citations"]
    assert len(citation_events) == 1
    payload = json.loads(citation_events[0]["data"])
    assert "citations" in payload
    assert len(payload["citations"]) == 1
    assert payload["citations"][0]["chunk_id"] == str(_CHUNK_ID)


@pytest.mark.asyncio
async def test_stream_emits_done_event_last(
    async_client: AsyncClient,
    override_db_stream: None,
    override_auth: None,
) -> None:
    async def _fake_stream(**kwargs: object) -> AsyncGenerator[str, None]:
        yield "Answer here."

    with (
        patch("app.api.v1.chat.RetrievalService") as mock_svc_cls,
        patch("app.api.v1.chat._call_llm_stream") as mock_stream,
    ):
        mock_svc = MagicMock()
        mock_svc.retrieve = AsyncMock(return_value=[])
        mock_svc_cls.return_value = mock_svc
        mock_stream.return_value = _fake_stream()

        response = await async_client.post(
            "/api/v1/chat/stream",
            json={
                "document_id": str(_DOCUMENT_ID),
                "question": "Done last?",
            },
        )

    events = _parse_sse(response.text)
    assert events[-1]["event"] == "done"


@pytest.mark.asyncio
async def test_stream_emits_error_event_on_llm_failure(
    async_client: AsyncClient,
    override_db_stream: None,
    override_auth: None,
) -> None:
    async def _failing_stream(**kwargs: object) -> AsyncGenerator[str, None]:
        raise RuntimeError("LLM blew up")
        yield  # make it a generator  # noqa: unreachable

    with (
        patch("app.api.v1.chat.RetrievalService") as mock_svc_cls,
        patch("app.api.v1.chat._call_llm_stream") as mock_stream,
    ):
        mock_svc = MagicMock()
        mock_svc.retrieve = AsyncMock(return_value=[])
        mock_svc_cls.return_value = mock_svc
        mock_stream.return_value = _failing_stream()

        response = await async_client.post(
            "/api/v1/chat/stream",
            json={
                "document_id": str(_DOCUMENT_ID),
                "question": "Will this fail?",
            },
        )

    import json

    events = _parse_sse(response.text)
    error_events = [e for e in events if e.get("event") == "error"]
    assert len(error_events) == 1
    payload = json.loads(error_events[0]["data"])
    assert "message" in payload
    assert payload["code"] == "CHAT_FAILED"


@pytest.mark.asyncio
async def test_stream_emits_error_event_when_document_not_found(
    async_client: AsyncClient,
    override_auth: None,
) -> None:
    async def _execute(stmt: object, params: object = None) -> MagicMock:  # noqa: ANN001
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        return result

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=_execute)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    async def _mock_get_db() -> AsyncGenerator[MagicMock, None]:
        yield mock_db

    app.dependency_overrides[get_db] = _mock_get_db
    try:
        response = await async_client.post(
            "/api/v1/chat/stream",
            json={
                "document_id": str(uuid.uuid4()),
                "question": "Anything?",
            },
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    import json

    events = _parse_sse(response.text)
    error_events = [e for e in events if e.get("event") == "error"]
    assert len(error_events) == 1
    payload = json.loads(error_events[0]["data"])
    assert payload["code"] == "DOCUMENT_NOT_FOUND"
