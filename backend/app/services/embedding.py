"""Embedding provider abstraction.

Priority:
  1. OpenAI  — if OPENAI_API_KEY is set (any environment)
  2. Ollama  — if APP_ENV=local and no OpenAI key (local dev fallback)
  3. Error   — production without an OpenAI key is a misconfiguration

OpenAI v3 models support the ``dimensions`` parameter, so EMBEDDING_DIMENSIONS
controls the output size for both providers.  When using Ollama, the chosen
model must natively output EMBEDDING_DIMENSIONS-dimensional vectors (e.g.
nomic-embed-text → 768 dims requires EMBEDDING_DIMENSIONS=768 in .env.local).
"""

from typing import Protocol

from openai import AsyncOpenAI

from app.core.settings import settings


class EmbeddingProvider(Protocol):
    """Duck-typed interface for embedding providers."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        ...


class OpenAIEmbeddingProvider:
    """Uses OpenAI text-embedding-3-* with configurable output dimensions."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_EMBED_MODEL
        self._dims = settings.EMBEDDING_DIMENSIONS

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
            dimensions=self._dims,
        )
        return [item.embedding for item in response.data]


class OllamaEmbeddingProvider:
    """Uses a local Ollama model via its OpenAI-compatible /v1/embeddings API."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama",  # Ollama ignores the key but the SDK requires one
        )
        self._model = settings.OLLAMA_EMBED_MODEL

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [item.embedding for item in response.data]


def get_embedding_provider() -> EmbeddingProvider:
    """Return the appropriate provider based on environment configuration."""
    if settings.OPENAI_API_KEY:
        return OpenAIEmbeddingProvider()
    if settings.APP_ENV == "local":
        return OllamaEmbeddingProvider()
    raise RuntimeError(
        "OPENAI_API_KEY must be set when APP_ENV is not 'local'. "
        "Add it to .env.prod or the production environment."
    )
