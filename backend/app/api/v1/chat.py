"""Chat endpoints — non-streaming and streaming RAG-backed Q&A."""

import json
import re
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langsmith import traceable
from loguru import logger
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.db.session import get_db
from app.models.chat_session import ChatSession
from app.models.document import Document, DocumentStatus
from app.models.message import Message, MessageRole
from app.schemas.chat import ChatRequest, ChatResponse, Citation
from app.schemas.common import ApiResponse
from app.services.retrieval import RetrievalService, RetrievedChunk

router = APIRouter(prefix="/chat", tags=["chat"])

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
    document_id: uuid.UUID,
    session_id: uuid.UUID | None,
) -> ChatSession:
    if session_id is not None:
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing
    # Create new session
    session = ChatSession(document_id=document_id)
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


# ---------------------------------------------------------------------------
# Provider labels — human-readable strings for API responses
# ---------------------------------------------------------------------------


def _llm_provider_label() -> str:
    if settings.OPENAI_API_KEY:
        return f"openai/{settings.OPENAI_CHAT_MODEL}"
    return f"ollama/{settings.OLLAMA_CHAT_MODEL}"


def _embed_provider_label() -> str:
    if settings.OPENAI_API_KEY:
        return f"openai/{settings.OPENAI_EMBED_MODEL}"
    return f"ollama/{settings.OLLAMA_EMBED_MODEL}"


# ---------------------------------------------------------------------------
# LLM client factory — OpenAI if key set, Ollama otherwise (local only)
# ---------------------------------------------------------------------------


def _get_llm_client() -> tuple[AsyncOpenAI, str]:
    """Return (client, model) for the appropriate LLM provider.

    Priority: OpenAI (if key set) > Ollama (APP_ENV=local) > RuntimeError.
    """
    if settings.OPENAI_API_KEY:
        return AsyncOpenAI(api_key=settings.OPENAI_API_KEY), settings.OPENAI_CHAT_MODEL
    if settings.APP_ENV == "local":
        client = AsyncOpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama",  # Ollama ignores this but SDK requires a value
        )
        return client, settings.OLLAMA_CHAT_MODEL
    raise RuntimeError(
        "OPENAI_API_KEY must be set when APP_ENV is not 'local'. "
        "Add it to .env.prod or the production environment."
    )


# ---------------------------------------------------------------------------
# LLM call (LangSmith traceable)
# ---------------------------------------------------------------------------


@traceable(name="chat_llm_call")
async def _call_llm(
    *,
    system_prompt: str,
    question: str,
    document_id: str,
    session_id: str,
) -> str:
    """Call the configured LLM and return the raw response text."""
    client, model = _get_llm_client()
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    )
    content = response.choices[0].message.content or ""
    return content


@traceable(name="chat_llm_stream")
async def _call_llm_stream(
    *,
    system_prompt: str,
    question: str,
    document_id: str,  # noqa: ARG001  — used by LangSmith tagging
    session_id: str,  # noqa: ARG001  — used by LangSmith tagging
) -> AsyncGenerator[str, None]:
    """Yield raw text tokens from a streaming LLM call."""
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
# POST /chat  (non-streaming)
# ---------------------------------------------------------------------------


@router.post("", status_code=202, response_model=ApiResponse[ChatResponse])
async def post_chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ApiResponse[ChatResponse]:
    """Non-streaming RAG chat endpoint."""
    doc = await _get_document_or_raise(db, body.document_id)

    chat_session = await _get_or_create_session(db, doc.id, body.session_id)

    # Persist user message
    user_msg = Message(
        session_id=chat_session.id,
        role=MessageRole.user,
        content=body.question,
    )
    db.add(user_msg)
    await db.flush()

    # Retrieve relevant chunks
    retrieval_svc = RetrievalService(db)
    chunks = await retrieval_svc.retrieve(body.question, doc.id, top_k=5)

    # Build prompt and call LLM
    system_prompt = _build_system_prompt(chunks)
    try:
        raw_answer = await _call_llm(
            system_prompt=system_prompt,
            question=body.question,
            document_id=str(body.document_id),
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

    # Persist assistant message
    assistant_msg = Message(
        session_id=chat_session.id,
        role=MessageRole.assistant,
        content=stripped_answer,
        citations=citation_dicts,
    )
    db.add(assistant_msg)
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
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> StreamingResponse:
    """Streaming RAG chat endpoint — Server-Sent Events."""

    async def _generate() -> AsyncGenerator[str, None]:
        try:
            doc = await _get_document_or_raise(db, body.document_id)
        except HTTPException as exc:
            raw = exc.detail
            detail: dict[str, object] = (
                raw if isinstance(raw, dict) else {"message": str(raw), "code": "ERROR"}
            )
            yield _sse_event(
                "error",
                {
                    "message": detail.get("message", ""),
                    "code": detail.get("code", "ERROR"),
                },
            )
            return

        chat_session = await _get_or_create_session(db, doc.id, body.session_id)

        user_msg = Message(
            session_id=chat_session.id,
            role=MessageRole.user,
            content=body.question,
        )
        db.add(user_msg)
        await db.flush()

        retrieval_svc = RetrievalService(db)
        try:
            chunks = await retrieval_svc.retrieve(body.question, doc.id, top_k=5)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "stream_retrieval_failed | document_id={}", body.document_id
            )
            yield _sse_event("error", {"message": str(exc), "code": "CHAT_FAILED"})
            return

        system_prompt = _build_system_prompt(chunks)

        # Stream tokens
        full_text = ""
        try:
            async for token in _call_llm_stream(
                system_prompt=system_prompt,
                question=body.question,
                document_id=str(body.document_id),
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
                "citations": citation_payloads,
                "llm_provider": _llm_provider_label(),
                "embed_provider": _embed_provider_label(),
            },
        )

        # Persist assistant message
        assistant_msg = Message(
            session_id=chat_session.id,
            role=MessageRole.assistant,
            content=stripped_answer,
            citations=citation_dicts,
        )
        db.add(assistant_msg)
        try:
            await db.commit()
        except Exception:  # noqa: BLE001
            pass  # Best effort — don't break SSE stream

        _ = found_in_document  # used implicitly via found_in_document

        yield _sse_event("done", {})

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
