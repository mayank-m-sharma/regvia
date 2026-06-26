# Tech Debts

## TD-001 — Embedding dimension coupling between providers

**File:** `backend/app/core/settings.py`, `backend/alembic/versions/a1b2c3d4e5f6_configurable_embedding_dimensions.py`

**Problem:** Switching embedding providers (OpenAI ↔ Ollama) may require a DB migration to resize the `embeddings.embedding` vector column if the two providers output different dimensions (OpenAI default: 1536, `nomic-embed-text`: 768). This makes provider switching painful — you need to update `EMBEDDING_DIMENSIONS`, run `alembic upgrade head`, and re-process all documents.

**Ideal fix:** Default `EMBEDDING_DIMENSIONS=768` for both providers. OpenAI `text-embedding-3-small` supports the `dimensions` param (Matryoshka), so it can output 768 natively. Both providers would always produce matching vectors, and the DB column would never need changing on a provider swap. The separate `a1b2c3d4e5f6` migration could be dropped and the initial schema updated to `vector(768)`.

**Priority:** Low — acceptable for now, just don't change `EMBEDDING_DIMENSIONS` without planning a re-processing job.
