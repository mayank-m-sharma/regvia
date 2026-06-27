"""Unit tests for POST /api/v1/chat (non-streaming)."""

import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.db.session import get_db
from app.main import app
from app.services.retrieval import RetrievedChunk

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_DOCUMENT_ID = uuid.uuid4()
_SESSION_ID = uuid.uuid4()
_CHUNK_ID = uuid.uuid4()
_MESSAGE_ID = uuid.uuid4()


def _make_ready_document(status: str = "ready") -> MagicMock:
    doc = MagicMock()
    doc.id = _DOCUMENT_ID
    doc.status = status
    return doc


def _make_chat_session() -> MagicMock:
    sess = MagicMock()
    sess.id = _SESSION_ID
    return sess


def _make_assistant_message() -> MagicMock:
    msg = MagicMock()
    msg.id = _MESSAGE_ID
    return msg


def _make_mock_db(
    document: MagicMock | None = None,
    session: MagicMock | None = None,
    message: MagicMock | None = None,
) -> MagicMock:
    if document is None:
        document = _make_ready_document()
    if session is None:
        session = _make_chat_session()
    if message is None:
        message = _make_assistant_message()

    # execute() is used for document lookup and session lookup
    call_count = 0

    async def _execute(stmt: object, params: object = None) -> MagicMock:  # noqa: ANN001
        nonlocal call_count
        result = MagicMock()
        if call_count == 0:
            # First call: document lookup
            result.scalar_one_or_none.return_value = document
        else:
            # Second call: session lookup (return None → create new)
            result.scalar_one_or_none.return_value = None
        call_count += 1
        return result

    # Track objects added; assign IDs on flush so ORM objects work
    _pending: list[object] = []

    def _add(obj: object) -> None:
        _pending.append(obj)
        # Eagerly set id so it's available immediately after add()
        if not hasattr(obj, "id") or getattr(obj, "id", None) is None:
            object.__setattr__(obj, "id", uuid.uuid4())

    async def _flush() -> None:
        for obj in _pending:
            if not hasattr(obj, "id") or getattr(obj, "id", None) is None:
                object.__setattr__(obj, "id", uuid.uuid4())

    async def _refresh(obj: object) -> None:
        if not hasattr(obj, "id") or getattr(obj, "id", None) is None:
            object.__setattr__(obj, "id", uuid.uuid4())
        object.__setattr__(obj, "created_at", datetime.now(UTC))

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(side_effect=_execute)
    mock_session.add = MagicMock(side_effect=_add)
    mock_session.flush = AsyncMock(side_effect=_flush)
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock(side_effect=_refresh)
    return mock_session


@pytest.fixture()
def override_db_ready() -> Generator[None, None, None]:
    """DB override returning a ready document."""

    async def _mock_get_db() -> AsyncGenerator[MagicMock, None]:
        yield _make_mock_db()

    app.dependency_overrides[get_db] = _mock_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


def _make_db_with_document_not_found() -> MagicMock:
    async def _execute(stmt: object, params: object = None) -> MagicMock:  # noqa: ANN001
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        return result

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(side_effect=_execute)
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    return mock_session


@pytest.fixture()
def override_db_not_found() -> Generator[None, None, None]:
    async def _mock_get_db() -> AsyncGenerator[MagicMock, None]:
        yield _make_db_with_document_not_found()

    app.dependency_overrides[get_db] = _mock_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


def _make_db_with_not_ready_document() -> MagicMock:
    async def _execute(stmt: object, params: object = None) -> MagicMock:  # noqa: ANN001
        result = MagicMock()
        doc = _make_ready_document(status="processing")
        result.scalar_one_or_none.return_value = doc
        return result

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(side_effect=_execute)
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    return mock_session


@pytest.fixture()
def override_db_not_ready() -> Generator[None, None, None]:
    async def _mock_get_db() -> AsyncGenerator[MagicMock, None]:
        yield _make_db_with_not_ready_document()

    app.dependency_overrides[get_db] = _mock_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


def _sample_chunks() -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            chunk_id=_CHUNK_ID,
            text="The regulation states that all entities must comply.",
            page_number=3,
            similarity=0.92,
        )
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_returns_202_with_answer_and_citations(
    async_client: AsyncClient,
    override_db_ready: None,
) -> None:
    answer_with_marker = f"All entities must comply. [chunk:{_CHUNK_ID}]"
    with (
        patch("app.api.v1.chat.RetrievalService") as mock_svc_cls,
        patch("app.api.v1.chat._call_llm", new_callable=AsyncMock) as mock_llm,
    ):
        mock_svc = MagicMock()
        mock_svc.retrieve = AsyncMock(return_value=_sample_chunks())
        mock_svc_cls.return_value = mock_svc
        mock_llm.return_value = answer_with_marker

        response = await async_client.post(
            "/api/v1/chat",
            json={
                "document_id": str(_DOCUMENT_ID),
                "question": "What must entities do?",
            },
        )

    assert response.status_code == 202
    data = response.json()["data"]
    assert data["answer"] == "All entities must comply."
    assert data["found_in_document"] is True
    assert len(data["citations"]) == 1
    assert data["citations"][0]["chunk_id"] == str(_CHUNK_ID)
    assert data["citations"][0]["page_number"] == 3


@pytest.mark.asyncio
async def test_chat_found_in_document_false_when_sentinel(
    async_client: AsyncClient,
    override_db_ready: None,
) -> None:
    sentinel = "I could not find this information in the document."
    with (
        patch("app.api.v1.chat.RetrievalService") as mock_svc_cls,
        patch("app.api.v1.chat._call_llm", new_callable=AsyncMock) as mock_llm,
    ):
        mock_svc = MagicMock()
        mock_svc.retrieve = AsyncMock(return_value=[])
        mock_svc_cls.return_value = mock_svc
        mock_llm.return_value = sentinel

        response = await async_client.post(
            "/api/v1/chat",
            json={
                "document_id": str(_DOCUMENT_ID),
                "question": "What is the answer to life?",
            },
        )

    assert response.status_code == 202
    data = response.json()["data"]
    assert data["found_in_document"] is False
    assert data["answer"] == sentinel


@pytest.mark.asyncio
async def test_chat_citation_markers_stripped_from_answer(
    async_client: AsyncClient,
    override_db_ready: None,
) -> None:
    cid1 = _CHUNK_ID
    cid2 = uuid.uuid4()
    chunks = [
        RetrievedChunk(
            chunk_id=cid1, text="First chunk text.", page_number=1, similarity=0.9
        ),
        RetrievedChunk(
            chunk_id=cid2, text="Second chunk text.", page_number=2, similarity=0.8
        ),
    ]
    raw = f"First point [chunk:{cid1}]. Second point [chunk:{cid2}]."
    with (
        patch("app.api.v1.chat.RetrievalService") as mock_svc_cls,
        patch("app.api.v1.chat._call_llm", new_callable=AsyncMock) as mock_llm,
    ):
        mock_svc = MagicMock()
        mock_svc.retrieve = AsyncMock(return_value=chunks)
        mock_svc_cls.return_value = mock_svc
        mock_llm.return_value = raw

        response = await async_client.post(
            "/api/v1/chat",
            json={
                "document_id": str(_DOCUMENT_ID),
                "question": "Tell me about compliance.",
            },
        )

    assert response.status_code == 202
    data = response.json()["data"]
    assert "[chunk:" not in data["answer"]
    assert len(data["citations"]) == 2


@pytest.mark.asyncio
async def test_chat_returns_404_when_document_not_found(
    async_client: AsyncClient,
    override_db_not_found: None,
) -> None:
    response = await async_client.post(
        "/api/v1/chat",
        json={
            "document_id": str(uuid.uuid4()),
            "question": "Anything?",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


@pytest.mark.asyncio
async def test_chat_returns_422_when_document_not_ready(
    async_client: AsyncClient,
    override_db_not_ready: None,
) -> None:
    response = await async_client.post(
        "/api/v1/chat",
        json={
            "document_id": str(_DOCUMENT_ID),
            "question": "Anything?",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_READY"


@pytest.mark.asyncio
async def test_chat_creates_new_session_when_session_id_null(
    async_client: AsyncClient,
    override_db_ready: None,
) -> None:
    with (
        patch("app.api.v1.chat.RetrievalService") as mock_svc_cls,
        patch("app.api.v1.chat._call_llm", new_callable=AsyncMock) as mock_llm,
    ):
        mock_svc = MagicMock()
        mock_svc.retrieve = AsyncMock(return_value=[])
        mock_svc_cls.return_value = mock_svc
        mock_llm.return_value = "I could not find this information in the document."

        response = await async_client.post(
            "/api/v1/chat",
            json={
                "document_id": str(_DOCUMENT_ID),
                "session_id": None,
                "question": "New session question?",
            },
        )

    assert response.status_code == 202
    data = response.json()["data"]
    assert "session_id" in data
    assert data["session_id"] is not None


@pytest.mark.asyncio
async def test_chat_reuses_existing_session_when_session_id_provided(
    async_client: AsyncClient,
) -> None:
    existing_session_id = uuid.uuid4()
    existing_session = MagicMock()
    existing_session.id = existing_session_id

    call_count = 0

    async def _execute(stmt: object, params: object = None) -> MagicMock:  # noqa: ANN001
        nonlocal call_count
        result = MagicMock()
        if call_count == 0:
            # Document lookup
            doc = _make_ready_document()
            result.scalar_one_or_none.return_value = doc
        else:
            # Session lookup — return existing session
            result.scalar_one_or_none.return_value = existing_session
        call_count += 1
        return result

    _pending2: list[object] = []

    def _add2(obj: object) -> None:
        _pending2.append(obj)
        if not hasattr(obj, "id") or getattr(obj, "id", None) is None:
            object.__setattr__(obj, "id", uuid.uuid4())

    async def _flush2() -> None:
        for obj in _pending2:
            if not hasattr(obj, "id") or getattr(obj, "id", None) is None:
                object.__setattr__(obj, "id", uuid.uuid4())

    async def _refresh2(obj: object) -> None:
        if not hasattr(obj, "id") or getattr(obj, "id", None) is None:
            object.__setattr__(obj, "id", uuid.uuid4())

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=_execute)
    mock_db.add = MagicMock(side_effect=_add2)
    mock_db.flush = AsyncMock(side_effect=_flush2)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=_refresh2)

    async def _mock_get_db() -> AsyncGenerator[MagicMock, None]:
        yield mock_db

    app.dependency_overrides[get_db] = _mock_get_db
    try:
        with (
            patch("app.api.v1.chat.RetrievalService") as mock_svc_cls,
            patch("app.api.v1.chat._call_llm", new_callable=AsyncMock) as mock_llm,
        ):
            mock_svc = MagicMock()
            mock_svc.retrieve = AsyncMock(return_value=[])
            mock_svc_cls.return_value = mock_svc
            mock_llm.return_value = "I could not find this information in the document."

            async with AsyncClient(
                transport=__import__("httpx").ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/chat",
                    json={
                        "document_id": str(_DOCUMENT_ID),
                        "session_id": str(existing_session_id),
                        "question": "Reuse session?",
                    },
                )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 202
    data = response.json()["data"]
    assert data["session_id"] == str(existing_session_id)
