"""Chat endpoints — non-streaming, streaming RAG Q&A, and session management."""

from __future__ import annotations

import json
import re
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from langsmith import traceable
from loguru import logger
from openai import AsyncOpenAI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user
from app.core.settings import settings
from app.db.session import get_db
from app.models.chat_session import ChatSession
from app.models.document import Document, DocumentStatus
from app.models.message import Message, MessageRole
from app.models.user import User
from app.schemas.chat import (
    ChatHistoryMessage,
    ChatRequest,
    ChatResponse,
    ChatSessionDetailResponse,
    ChatSessionResponse,
    Citation,
    CreateSessionRequest,
)
from app.schemas.common import ApiResponse
from app.services.retrieval import RetrievalService, RetrievedChunk
from app.services.title_service import generate_session_title

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(get_current_user)],
)

_NOT_FOUND_SENTINEL = "I could not find this information in the document."
_CHUNK_MARKER_RE = re.compile(r"\[chunk:([0-9a-f\-]{36})\]", re.IGNORECASE)

_SYSTEM_PROMPT_TEMPLATE = (
    "You are a compliance assistant. Answer the user's question using ONLY the"
    " context provided below. If the answer is not present in the context,"
    ' respond with exactly: "I could not find this information in the document."\n'
    "Do not infer, extrapolate, or use outside knowledge.\n"
    "For each claim you make, indicate the source chunk ID in square brackets,"
    " e.g. [chunk:uuid].\n\n"
    "Context:\n{chunks_text}"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_chunks_text(chunks: list[RetrievedChunk]) -> str:
    lines: list[str] = []
    for c in chunks:
        page = f"page {c.page_number}" if c.page_number is not None else "page unknown"
        lines.append(f"[chunk:{c.chunk_id}] ({page}): {c.text}")
    return "\n".join(lines)


def _build_system_prompt(chunks: list[RetrievedChunk]) -> str:
    return _SYSTEM_PROMPT_TEMPLATE.format(chunks_text=_build_chunks_text(chunks))


def _extract_citations(
    raw_answer: str, chunks: list[RetrievedChunk]
) -> tuple[str, list[Citation]]:
    """Strip [chunk:uuid] markers from *raw_answer* and build citation list."""
    chunk_map = {str(c.chunk_id): c for c in chunks}
    seen_ids: set[str] = set()
    citations: list[Citation] = []

    for match in _CHUNK_MARKER_RE.finditer(raw_answer):
        cid = match.group(1).lower()
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        if cid in chunk_map:
            c = chunk_map[cid]
            citations.append(
                Citation(
                    chunk_id=c.chunk_id,
                    page_number=c.page_number,
                    excerpt=c.text[:200],
                )
            )

    stripped = _CHUNK_MARKER_RE.sub("", raw_answer).strip()
    return stripped, citations


async def _get_or_create_session(
    db: AsyncSession,
    document_id: uuid.UUID | None,
    session_id: uuid.UUID | None,
    user_id: uuid.UUID,
) -> ChatSession:
    if session_id is not None:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing
    session = ChatSession(document_id=document_id, user_id=user_id)
    db.add(session)
    await db.flush()
    return session


async def _get_document_or_raise(db: AsyncSession, document_id: uuid.UUID) -> Document:
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail={"message": "Document not found.", "code": "DOCUMENT_NOT_FOUND"},
        )
    if doc.status != DocumentStatus.ready:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Document is not ready for querying.",
                "code": "DOCUMENT_NOT_READY",
            },
        )
    return doc


def _llm_provider_label() -> str:
    if settings.OPENAI_API_KEY:
        return f"openai/{settings.OPENAI_CHAT_MODEL}"
    return f"ollama/{settings.OLLAMA_CHAT_MODEL}"


def _embed_provider_label() -> str:
    if settings.OPENAI_API_KEY:
        return f"openai/{settings.OPENAI_EMBED_MODEL}"
    return f"ollama/{settings.OLLAMA_EMBED_MODEL}"


def _get_llm_client() -> tuple[AsyncOpenAI, str]:
    if settings.OPENAI_API_KEY:
        return AsyncOpenAI(api_key=settings.OPENAI_API_KEY), settings.OPENAI_CHAT_MODEL
    if settings.APP_ENV == "local":
        client = AsyncOpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama",
        )
        return client, settings.OLLAMA_CHAT_MODEL
    raise RuntimeError("OPENAI_API_KEY must be set when APP_ENV is not 'local'.")


@traceable(name="chat_llm_call")
async def _call_llm(
    *,
    system_prompt: str,
    question: str,
    document_id: str,
    session_id: str,
) -> str:
    client, model = _get_llm_client()
    t0 = time.monotonic()
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    )
    latency_ms = round((time.monotonic() - t0) * 1000, 1)
    usage = response.usage
    logger.info(
        "llm_call | model={} prompt_tokens={} completion_tokens={} latency_ms={}",
        model,
        usage.prompt_tokens if usage else None,
        usage.completion_tokens if usage else None,
        latency_ms,
    )
    content = response.choices[0].message.content or ""
    return content


@traceable(name="chat_llm_stream")
async def _call_llm_stream(
    *,
    system_prompt: str,
    question: str,
    document_id: str,  # noqa: ARG001
    session_id: str,  # noqa: ARG001
) -> AsyncGenerator[str, None]:
    client, model = _get_llm_client()
    stream = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta


# ---------------------------------------------------------------------------
# Session management endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/sessions",
    status_code=201,
    response_model=ApiResponse[ChatSessionResponse],
)
async def create_session(
    body: CreateSessionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[ChatSessionResponse]:
    """Create a new empty chat session.

    Pass ``document_id`` for a document-specific session; omit it (or pass
    ``null``) for a Knowledge Library session.
    """
    doc_filename: str | None = None
    if body.document_id is not None:
        result = await db.execute(
            select(Document).where(Document.id == body.document_id)
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Document not found.",
                    "code": "DOCUMENT_NOT_FOUND",
                },
            )
        doc_filename = doc.filename

    session = ChatSession(document_id=body.document_id, user_id=current_user.id)
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return ApiResponse(
        data=ChatSessionResponse(
            id=session.id,
            document_id=session.document_id,
            document_filename=doc_filename,
            title=session.title,
            created_at=session.created_at,
            last_message_at=session.last_message_at,
            message_count=0,
        )
    )


@router.get("/sessions", response_model=ApiResponse[list[ChatSessionResponse]])
async def list_sessions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[list[ChatSessionResponse]]:
    """List all chat sessions for the current user, sorted by recency."""
    # Subquery: message count per session
    msg_count_sq = (
        select(
            Message.session_id,
            func.count(Message.id).label("message_count"),
        )
        .group_by(Message.session_id)
        .subquery()
    )

    rows = await db.execute(
        select(ChatSession, Document.filename, msg_count_sq.c.message_count)
        .outerjoin(Document, ChatSession.document_id == Document.id)
        .outerjoin(msg_count_sq, ChatSession.id == msg_count_sq.c.session_id)
        .where(ChatSession.user_id == current_user.id)
        .order_by(
            ChatSession.last_message_at.desc().nulls_last(),
            ChatSession.created_at.desc(),
        )
    )

    sessions = []
    for chat_session, filename, msg_count in rows:
        sessions.append(
            ChatSessionResponse(
                id=chat_session.id,
                document_id=chat_session.document_id,
                document_filename=filename,
                title=chat_session.title,
                created_at=chat_session.created_at,
                last_message_at=chat_session.last_message_at,
                message_count=msg_count or 0,
            )
        )

    return ApiResponse(data=sessions)


@router.get(
    "/sessions/{session_id}",
    response_model=ApiResponse[ChatSessionDetailResponse],
)
async def get_session(
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[ChatSessionDetailResponse]:
    """Fetch a single session with its full message history."""
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages), selectinload(ChatSession.document))
        .where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Session not found.", "code": "SESSION_NOT_FOUND"},
        )

    messages = [
        ChatHistoryMessage(
            id=m.id,
            role=m.role.value,
            content=m.content,
            citations=[
                Citation(
                    chunk_id=c["chunk_id"],
                    page_number=c.get("page_number"),
                    excerpt=c.get("excerpt", ""),
                )
                for c in (m.citations or [])
            ],
            created_at=m.created_at,
        )
        for m in session.messages
    ]

    return ApiResponse(
        data=ChatSessionDetailResponse(
            id=session.id,
            document_id=session.document_id,
            document_filename=session.document.filename if session.document else None,
            title=session.title,
            created_at=session.created_at,
            last_message_at=session.last_message_at,
            messages=messages,
        )
    )


# ---------------------------------------------------------------------------
# POST /chat  (non-streaming)
# ---------------------------------------------------------------------------


@router.post("", status_code=202, response_model=ApiResponse[ChatResponse])
async def post_chat(
    body: ChatRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[ChatResponse]:
    """Non-streaming RAG chat endpoint."""
    retrieval_svc = RetrievalService(db)
    if body.document_id is not None:
        doc = await _get_document_or_raise(db, body.document_id)
        session_document_id: uuid.UUID | None = doc.id
        chunks = await retrieval_svc.retrieve(body.question, doc.id, top_k=5)
    else:
        session_document_id = None
        chunks = await retrieval_svc.retrieve_from_library(
            body.question, current_user.id, top_k=10
        )

    chat_session = await _get_or_create_session(
        db, session_document_id, body.session_id, current_user.id
    )
    is_first_exchange = chat_session.last_message_at is None

    user_msg = Message(
        session_id=chat_session.id,
        role=MessageRole.user,
        content=body.question,
        created_at=datetime.now(UTC),
    )
    db.add(user_msg)
    await db.flush()

    system_prompt = _build_system_prompt(chunks)
    try:
        raw_answer = await _call_llm(
            system_prompt=system_prompt,
            question=body.question,
            document_id=str(body.document_id) if body.document_id else "library",
            session_id=str(chat_session.id),
        )
    except Exception as exc:
        logger.exception(
            "chat_llm_failed | document_id={} session_id={}",
            body.document_id,
            chat_session.id,
        )
        raise HTTPException(
            status_code=500,
            detail={"message": "LLM call failed.", "code": "CHAT_FAILED"},
        ) from exc

    stripped_answer, citations = _extract_citations(raw_answer, chunks)
    found_in_document = stripped_answer.strip() != _NOT_FOUND_SENTINEL

    citation_dicts: list[dict[str, object]] = [
        c.model_dump(mode="json") for c in citations
    ]

    assistant_msg = Message(
        session_id=chat_session.id,
        role=MessageRole.assistant,
        content=stripped_answer,
        citations=citation_dicts,
        created_at=datetime.now(UTC),
    )
    db.add(assistant_msg)

    now = datetime.now(UTC)
    chat_session.last_message_at = now

    if is_first_exchange and chat_session.title is None:
        chat_session.title = await generate_session_title(
            body.question, stripped_answer
        )

    await db.commit()
    await db.refresh(assistant_msg)

    return ApiResponse(
        data=ChatResponse(
            session_id=chat_session.id,
            message_id=assistant_msg.id,
            answer=stripped_answer,
            citations=citations,
            found_in_document=found_in_document,
            llm_provider=_llm_provider_label(),
            embed_provider=_embed_provider_label(),
        )
    )


# ---------------------------------------------------------------------------
# POST /chat/stream  (SSE)
# ---------------------------------------------------------------------------


def _sse_event(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/stream")
async def post_chat_stream(
    body: ChatRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    """Streaming RAG chat endpoint — Server-Sent Events."""

    async def _generate() -> AsyncGenerator[str, None]:
        # ── Retrieval: single doc or library ──────────────────────────────
        retrieval_svc = RetrievalService(db)
        if body.document_id is not None:
            try:
                doc = await _get_document_or_raise(db, body.document_id)
            except HTTPException as exc:
                raw = exc.detail
                detail: dict[str, object] = (
                    raw
                    if isinstance(raw, dict)
                    else {"message": str(raw), "code": "ERROR"}
                )
                yield _sse_event(
                    "error",
                    {
                        "message": detail.get("message", ""),
                        "code": detail.get("code", "ERROR"),
                    },
                )
                return
            stream_document_id: uuid.UUID | None = doc.id
        else:
            stream_document_id = None

        chat_session = await _get_or_create_session(
            db, stream_document_id, body.session_id, current_user.id
        )
        is_first_exchange = chat_session.last_message_at is None

        user_msg = Message(
            session_id=chat_session.id,
            role=MessageRole.user,
            content=body.question,
            created_at=datetime.now(UTC),
        )
        db.add(user_msg)
        await db.flush()

        try:
            if stream_document_id is not None:
                chunks = await retrieval_svc.retrieve(
                    body.question, stream_document_id, top_k=5
                )
            else:
                chunks = await retrieval_svc.retrieve_from_library(
                    body.question, current_user.id, top_k=10
                )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "stream_retrieval_failed | document_id={}", body.document_id
            )
            yield _sse_event("error", {"message": str(exc), "code": "CHAT_FAILED"})
            return

        system_prompt = _build_system_prompt(chunks)

        full_text = ""
        try:
            async for token in _call_llm_stream(
                system_prompt=system_prompt,
                question=body.question,
                document_id=str(body.document_id) if body.document_id else "library",
                session_id=str(chat_session.id),
            ):
                full_text += token
                yield _sse_event("token", {"token": token})
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "stream_llm_failed | document_id={} session_id={}",
                body.document_id,
                chat_session.id,
            )
            yield _sse_event("error", {"message": str(exc), "code": "CHAT_FAILED"})
            return

        stripped_answer, citations = _extract_citations(full_text, chunks)
        found_in_document = stripped_answer.strip() != _NOT_FOUND_SENTINEL

        citation_dicts: list[dict[str, object]] = [
            c.model_dump(mode="json") for c in citations
        ]
        citation_payloads = [
            {
                "chunk_id": str(c.chunk_id),
                "page_number": c.page_number,
                "excerpt": c.excerpt,
            }
            for c in citations
        ]

        yield _sse_event(
            "citations",
            {
                "session_id": str(chat_session.id),
                "citations": citation_payloads,
                "llm_provider": _llm_provider_label(),
                "embed_provider": _embed_provider_label(),
            },
        )

        assistant_msg = Message(
            session_id=chat_session.id,
            role=MessageRole.assistant,
            content=stripped_answer,
            citations=citation_dicts,
            created_at=datetime.now(UTC),
        )
        db.add(assistant_msg)

        now = datetime.now(UTC)
        chat_session.last_message_at = now

        if is_first_exchange and chat_session.title is None:
            chat_session.title = await generate_session_title(
                body.question, stripped_answer
            )

        try:
            await db.commit()
        except Exception:  # noqa: BLE001
            pass  # Best effort — don't break SSE stream

        _ = found_in_document

        yield _sse_event("done", {"session_id": str(chat_session.id)})

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
