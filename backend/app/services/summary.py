"""Compliance summary service — generates and caches structured summaries."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from langsmith import traceable
from loguru import logger
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.models.chunk import Chunk
from app.models.document import Document, DocumentStatus
from app.models.summary import Summary
from app.schemas.summary import (
    Gap,
    Obligation,
    Recommendation,
    Risk,
    SeverityLevel,
    SummaryResponse,
)

# ---------------------------------------------------------------------------
# LLM client factory
# ---------------------------------------------------------------------------

_DIRECT_SYSTEM_PROMPT_PREFIX = (
    "You are a compliance document analyst. Extract structured compliance information"
    " from the document chunks below.\n\n"
    "Return a JSON object with exactly these keys:\n"
    "- obligations: list of objects with keys text, page_number, chunk_id"
    " — regulatory obligations the organisation must meet\n"
    "- risks: list of objects with keys text, severity (high/medium/low),"
    " page_number, chunk_id — identified compliance risks\n"
    "- gaps: list of objects with keys text, page_number, chunk_id"
    " — areas where compliance is missing or unclear\n"
    "- recommendations: list of objects with keys text, priority (high/medium/low)"
    " — suggested actions\n\n"
    "Use null for page_number/chunk_id when not determinable. Return valid JSON"
    " only.\n\n"
    "Chunks:\n"
)

_MAP_SYSTEM_PROMPT_PREFIX = (
    "You are a compliance document analyst. Extract key compliance information from the"
    " document chunks below as bullet points.\n\n"
    "Return a JSON object with these keys:\n"
    "- obligations: list of strings — regulatory obligations\n"
    "- risks: list of strings — compliance risks with severity noted\n"
    "- gaps: list of strings — compliance gaps\n"
    "- recommendations: list of strings — suggested actions with priority noted\n\n"
    "Return valid JSON only.\n\n"
    "Chunks:\n"
)

_REDUCE_SYSTEM_PROMPT_PREFIX = (
    "You are a compliance document analyst. Combine and deduplicate the following"
    " mini-summaries extracted from document batches into a single structured"
    " compliance summary.\n\n"
    "Return a JSON object with exactly these keys:\n"
    "- obligations: list of objects with keys text, page_number, chunk_id"
    " — regulatory obligations\n"
    "- risks: list of objects with keys text, severity (high/medium/low),"
    " page_number, chunk_id — identified compliance risks\n"
    "- gaps: list of objects with keys text, page_number, chunk_id"
    " — areas where compliance is missing or unclear\n"
    "- recommendations: list of objects with keys text, priority (high/medium/low)"
    " — suggested actions\n\n"
    "Set page_number and chunk_id to null (they are not available at this stage)."
    " Return valid JSON only.\n\n"
    "Mini-summaries:\n"
)


def _get_summary_llm_client() -> tuple[AsyncOpenAI, str]:
    """Return (client, model) for the summary LLM provider.

    Priority: OpenAI (if key set) > Ollama (APP_ENV=local) > RuntimeError.
    """
    if settings.OPENAI_API_KEY:
        return (
            AsyncOpenAI(api_key=settings.OPENAI_API_KEY),
            settings.OPENAI_SUMMARY_MODEL,
        )
    if settings.APP_ENV == "local":
        client = AsyncOpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama",  # Ollama ignores this but SDK requires a value
        )
        return client, settings.OLLAMA_SUMMARY_MODEL
    raise RuntimeError(
        "OPENAI_API_KEY must be set when APP_ENV is not 'local'. "
        "Add it to .env.prod or the production environment."
    )


def _build_chunks_text(chunks: list[Chunk]) -> str:
    lines: list[str] = []
    for c in chunks:
        page = f"page {c.page_number}" if c.page_number is not None else "page unknown"
        lines.append(f"[chunk:{c.id}] ({page}): {c.text}")
    return "\n".join(lines)


def _parse_llm_json(content: str) -> dict[str, Any]:  # noqa: ANN401
    """Parse JSON from LLM response, stripping markdown fences if present."""
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first and last fence lines
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner)
    return json.loads(text)  # type: ignore[no-any-return]


def _coerce_obligations(raw: list[Any]) -> list[Obligation]:  # noqa: ANN401
    result: list[Obligation] = []
    for item in raw:
        if isinstance(item, dict):
            result.append(
                Obligation(
                    text=str(item.get("text", "")),
                    page_number=item.get("page_number"),
                    chunk_id=item.get("chunk_id"),
                )
            )
        else:
            result.append(Obligation(text=str(item), page_number=None, chunk_id=None))
    return result


def _coerce_risks(raw: list[Any]) -> list[Risk]:  # noqa: ANN401
    result: list[Risk] = []
    for item in raw:
        if isinstance(item, dict):
            severity_raw = str(item.get("severity", "medium")).lower()
            try:
                severity = SeverityLevel(severity_raw)
            except ValueError:
                severity = SeverityLevel.medium
            result.append(
                Risk(
                    text=str(item.get("text", "")),
                    severity=severity,
                    page_number=item.get("page_number"),
                    chunk_id=item.get("chunk_id"),
                )
            )
        else:
            result.append(
                Risk(
                    text=str(item),
                    severity=SeverityLevel.medium,
                    page_number=None,
                    chunk_id=None,
                )
            )
    return result


def _coerce_gaps(raw: list[Any]) -> list[Gap]:  # noqa: ANN401
    result: list[Gap] = []
    for item in raw:
        if isinstance(item, dict):
            result.append(
                Gap(
                    text=str(item.get("text", "")),
                    page_number=item.get("page_number"),
                    chunk_id=item.get("chunk_id"),
                )
            )
        else:
            result.append(Gap(text=str(item), page_number=None, chunk_id=None))
    return result


def _coerce_recommendations(raw: list[Any]) -> list[Recommendation]:  # noqa: ANN401
    result: list[Recommendation] = []
    for item in raw:
        if isinstance(item, dict):
            priority_raw = str(item.get("priority", "medium")).lower()
            try:
                priority = SeverityLevel(priority_raw)
            except ValueError:
                priority = SeverityLevel.medium
            result.append(
                Recommendation(
                    text=str(item.get("text", "")),
                    priority=priority,
                )
            )
        else:
            result.append(Recommendation(text=str(item), priority=SeverityLevel.medium))
    return result


# ---------------------------------------------------------------------------
# LLM call helpers (LangSmith traceable)
# ---------------------------------------------------------------------------


@traceable(name="summary_llm_call")
async def _call_summary_llm(
    *,
    system_prompt: str,
    document_id: str,
    strategy: str,
    chunk_count: int,
) -> str:
    """Call the configured summary LLM and return the raw response text."""
    client, model = _get_summary_llm_client()
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": system_prompt}],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    return content


@traceable(name="summary_map_call")
async def _call_map_llm(
    *,
    system_prompt: str,
    document_id: str,
    batch_index: int,
    chunk_count: int,
) -> str:
    """Call the LLM for a single map batch and return raw JSON text."""
    client, model = _get_summary_llm_client()
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": system_prompt}],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    return content


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class SummaryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_generate(self, document_id: UUID) -> SummaryResponse:
        """Return a cached summary or generate a new one and persist it."""
        # 1. Check cache
        cached_stmt = select(Summary).where(Summary.document_id == document_id)
        cached_result = await self._session.execute(cached_stmt)
        cached_row = cached_result.scalar_one_or_none()

        if cached_row is not None:
            logger.info("summary_cache_hit | document_id={}", document_id)
            return self._row_to_response(cached_row, cached=True)

        # 2. Fetch chunks
        stmt = (
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
        )
        result = await self._session.execute(stmt)
        chunks = list(result.scalars().all())

        chunk_count = len(chunks)
        logger.info(
            "summary_generating | document_id={} chunk_count={}",
            document_id,
            chunk_count,
        )

        if chunk_count <= settings.SUMMARY_DIRECT_CHUNK_LIMIT:
            obligations, risks, gaps, recommendations = await self._direct_strategy(
                chunks=chunks,
                document_id=document_id,
            )
        else:
            obligations, risks, gaps, recommendations = await self._map_reduce_strategy(
                chunks=chunks,
                document_id=document_id,
            )

        # 3. Persist
        generated_at = datetime.now(UTC)
        summary_row = Summary(
            document_id=document_id,
            obligations=[o.model_dump(mode="json") for o in obligations],
            risks=[r.model_dump(mode="json") for r in risks],
            gaps=[g.model_dump(mode="json") for g in gaps],
            recommendations=[rec.model_dump(mode="json") for rec in recommendations],
            generated_at=generated_at,
        )
        self._session.add(summary_row)
        await self._session.commit()
        await self._session.refresh(summary_row)

        return SummaryResponse(
            document_id=document_id,
            obligations=obligations,
            risks=risks,
            gaps=gaps,
            recommendations=recommendations,
            generated_at=generated_at,
            cached=False,
        )

    async def _direct_strategy(
        self,
        *,
        chunks: list[Chunk],
        document_id: UUID,
    ) -> tuple[list[Obligation], list[Risk], list[Gap], list[Recommendation]]:
        chunks_text = _build_chunks_text(chunks)
        system_prompt = _DIRECT_SYSTEM_PROMPT_PREFIX + chunks_text

        raw = await _call_summary_llm(
            system_prompt=system_prompt,
            document_id=str(document_id),
            strategy="direct",
            chunk_count=len(chunks),
        )
        parsed = _parse_llm_json(raw)
        return (
            _coerce_obligations(parsed.get("obligations", [])),
            _coerce_risks(parsed.get("risks", [])),
            _coerce_gaps(parsed.get("gaps", [])),
            _coerce_recommendations(parsed.get("recommendations", [])),
        )

    async def _map_reduce_strategy(
        self,
        *,
        chunks: list[Chunk],
        document_id: UUID,
    ) -> tuple[list[Obligation], list[Risk], list[Gap], list[Recommendation]]:
        batch_size = 10
        mini_summaries: list[str] = []

        for batch_index, i in enumerate(range(0, len(chunks), batch_size)):
            batch = chunks[i : i + batch_size]
            chunks_text = _build_chunks_text(batch)
            system_prompt = _MAP_SYSTEM_PROMPT_PREFIX + chunks_text

            raw = await _call_map_llm(
                system_prompt=system_prompt,
                document_id=str(document_id),
                batch_index=batch_index,
                chunk_count=len(batch),
            )
            mini_summaries.append(raw)

        summaries_text = "\n\n---\n\n".join(
            f"Batch {i + 1}:\n{s}" for i, s in enumerate(mini_summaries)
        )
        reduce_prompt = _REDUCE_SYSTEM_PROMPT_PREFIX + summaries_text

        raw_final = await _call_summary_llm(
            system_prompt=reduce_prompt,
            document_id=str(document_id),
            strategy="map_reduce",
            chunk_count=len(chunks),
        )
        parsed = _parse_llm_json(raw_final)
        return (
            _coerce_obligations(parsed.get("obligations", [])),
            _coerce_risks(parsed.get("risks", [])),
            _coerce_gaps(parsed.get("gaps", [])),
            _coerce_recommendations(parsed.get("recommendations", [])),
        )

    @staticmethod
    def _row_to_response(row: Summary, *, cached: bool) -> SummaryResponse:
        return SummaryResponse(
            document_id=row.document_id,
            obligations=[Obligation.model_validate(o) for o in row.obligations],
            risks=[Risk.model_validate(r) for r in row.risks],
            gaps=[Gap.model_validate(g) for g in row.gaps],
            recommendations=[
                Recommendation.model_validate(r) for r in row.recommendations
            ],
            generated_at=row.generated_at,
            cached=cached,
        )


# ---------------------------------------------------------------------------
# Document validation helper (used by endpoint)
# ---------------------------------------------------------------------------


async def get_document_or_raise_for_summary(
    db: AsyncSession,
    document_id: UUID,
) -> Document:
    """Fetch document, raising 404/422 as appropriate for summary endpoint."""
    from fastapi import HTTPException  # local import to avoid circular deps

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
