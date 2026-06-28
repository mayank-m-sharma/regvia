"""Pydantic schemas for the chat endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    document_id: uuid.UUID | None = None  # None → library mode (search all user docs)
    session_id: uuid.UUID | None = None
    question: str


class Citation(BaseModel):
    chunk_id: uuid.UUID
    page_number: int | None
    excerpt: str  # first 200 chars of chunk text


class ChatResponse(BaseModel):
    session_id: uuid.UUID
    message_id: uuid.UUID
    answer: str
    citations: list[Citation]
    found_in_document: bool
    llm_provider: str  # e.g. "openai/gpt-4o-mini" or "ollama/llama3.2"
    embed_provider: str  # e.g. "openai/text-embedding-3-small" or "ollama/nomic-embed-text"  # noqa: E501


# ---------------------------------------------------------------------------
# Session management schemas (REGVIA-029 / REGVIA-030)
# ---------------------------------------------------------------------------


class CreateSessionRequest(BaseModel):
    document_id: uuid.UUID | None = None  # None → library session


class ChatHistoryMessage(BaseModel):
    id: uuid.UUID
    role: str  # "user" | "assistant"
    content: str
    citations: list[Citation]
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID | None  # None for library sessions
    document_filename: str | None  # populated from join
    title: str | None
    created_at: datetime
    last_message_at: datetime | None
    message_count: int

    model_config = {"from_attributes": True}


class ChatSessionDetailResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID | None  # None for library sessions
    document_filename: str | None
    title: str | None
    created_at: datetime
    last_message_at: datetime | None
    messages: list[ChatHistoryMessage]

    model_config = {"from_attributes": True}
