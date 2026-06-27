"""Pydantic schemas for the chat endpoints."""

import uuid

from pydantic import BaseModel


class ChatRequest(BaseModel):
    document_id: uuid.UUID
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
