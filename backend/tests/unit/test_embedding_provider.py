"""Unit tests for the embedding provider abstraction."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.embedding import (
    OllamaEmbeddingProvider,
    OpenAIEmbeddingProvider,
    get_embedding_provider,
)

# ---------------------------------------------------------------------------
# get_embedding_provider — selection logic
# ---------------------------------------------------------------------------


def test_selects_openai_when_api_key_set() -> None:
    with patch("app.services.embedding.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "sk-test"
        mock_settings.APP_ENV = "local"
        provider = get_embedding_provider()
    assert isinstance(provider, OpenAIEmbeddingProvider)


def test_selects_ollama_when_no_key_and_local_env() -> None:
    with patch("app.services.embedding.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = ""
        mock_settings.APP_ENV = "local"
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.OLLAMA_EMBED_MODEL = "nomic-embed-text"
        provider = get_embedding_provider()
    assert isinstance(provider, OllamaEmbeddingProvider)


def test_openai_takes_priority_over_ollama_when_key_set() -> None:
    with patch("app.services.embedding.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "sk-test"
        mock_settings.APP_ENV = "local"  # local env but key is present
        provider = get_embedding_provider()
    assert isinstance(provider, OpenAIEmbeddingProvider)


def test_raises_in_production_without_api_key() -> None:
    with patch("app.services.embedding.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = ""
        mock_settings.APP_ENV = "production"
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY must be set"):
            get_embedding_provider()


# ---------------------------------------------------------------------------
# OpenAIEmbeddingProvider.embed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openai_provider_calls_embeddings_create() -> None:
    fake_embedding = [0.1] * 1536
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=fake_embedding)]

    with patch("app.services.embedding.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "sk-test"
        mock_settings.OPENAI_EMBED_MODEL = "text-embedding-3-small"
        mock_settings.EMBEDDING_DIMENSIONS = 1536

        with patch("app.services.embedding.AsyncOpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)
            mock_openai_cls.return_value = mock_client

            provider = OpenAIEmbeddingProvider()
            result = await provider.embed(["hello world"])

    mock_client.embeddings.create.assert_called_once_with(
        model="text-embedding-3-small",
        input=["hello world"],
        dimensions=1536,
    )
    assert result == [fake_embedding]


@pytest.mark.asyncio
async def test_openai_provider_returns_one_vector_per_input() -> None:
    texts = ["doc one", "doc two", "doc three"]
    fake_embeddings = [[float(i)] * 1536 for i in range(len(texts))]
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=e) for e in fake_embeddings]

    with patch("app.services.embedding.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "sk-test"
        mock_settings.OPENAI_EMBED_MODEL = "text-embedding-3-small"
        mock_settings.EMBEDDING_DIMENSIONS = 1536

        with patch("app.services.embedding.AsyncOpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)
            mock_openai_cls.return_value = mock_client

            provider = OpenAIEmbeddingProvider()
            result = await provider.embed(texts)

    assert len(result) == 3
    assert result == fake_embeddings


# ---------------------------------------------------------------------------
# OllamaEmbeddingProvider.embed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ollama_provider_calls_embeddings_create() -> None:
    fake_embedding = [0.2] * 768
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=fake_embedding)]

    with patch("app.services.embedding.settings") as mock_settings:
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.OLLAMA_EMBED_MODEL = "nomic-embed-text"

        with patch("app.services.embedding.AsyncOpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)
            mock_openai_cls.return_value = mock_client

            provider = OllamaEmbeddingProvider()
            result = await provider.embed(["hello world"])

    mock_openai_cls.assert_called_once_with(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
    )
    mock_client.embeddings.create.assert_called_once_with(
        model="nomic-embed-text",
        input=["hello world"],
    )
    assert result == [fake_embedding]


@pytest.mark.asyncio
async def test_ollama_provider_returns_one_vector_per_input() -> None:
    texts = ["first", "second"]
    fake_embeddings = [[float(i)] * 768 for i in range(len(texts))]
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=e) for e in fake_embeddings]

    with patch("app.services.embedding.settings") as mock_settings:
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.OLLAMA_EMBED_MODEL = "nomic-embed-text"

        with patch("app.services.embedding.AsyncOpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)
            mock_openai_cls.return_value = mock_client

            provider = OllamaEmbeddingProvider()
            result = await provider.embed(texts)

    assert len(result) == 2
    assert result == fake_embeddings
