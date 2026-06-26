# RegVia — Compliance Copilot: Master Jira Spec

> **Spec-Driven Development (SDD)** — All implementation must trace back to a ticket here.
> Every ticket is atomic, sequenced, and implementation-ready.

---

## Epic Map

| ID | Epic | Area | Status |
|----|------|------|--------|
| E1 | Repo & Tooling Bootstrap | Infra | ✅ Done |
| E1.5 | Test Infrastructure | Full-Stack | ✅ Done |
| E2 | Database & Storage Layer | Backend | 🔄 In Progress |
| E3 | Document Upload & Processing | Backend | |
| E4 | RAG Pipeline | Backend/AI | |
| E5 | Compliance Summary | Backend/AI | |
| E6 | Streaming & Background Jobs | Backend | |
| E7 | Observability & Logging | Backend/AI | |
| E8 | Frontend Foundation | Frontend | |
| E9 | Document Feature (Upload UI) | Frontend | |
| E10 | Chat Feature (Q&A UI) | Frontend | |
| E11 | Summary Feature (Summary UI) | Frontend | |
| E12 | Testing (Feature Tests) | Full-Stack | |
| E13 | Deployment & CI/CD | Infra | |

> **Test-First Policy:** E1.5 sets up the test infrastructure before any feature work begins.
> Every feature ticket in E2–E11 is expected to ship with its own tests written alongside it.
> E12 covers integration tests and coverage gates — not first-time test setup.

---

## E1 — Repo & Tooling Bootstrap ✅

---

### ✅ REGVIA-001 · Initialize monorepo structure

**Problem Statement**
No project exists yet. We need a clean, reproducible workspace before any code is written.

**User Story**
As an engineer, I need a versioned monorepo with consistent tooling so I can develop without environment drift.

**Description**
Create the `regVia/` root directory containing `frontend/`, `backend/`, and `infra/` sub-repos. Each sub-repo gets its own `package.json` / `pyproject.toml`. Root-level `docker-compose.yml` wires local services together.

**Technical Details**
- Root: `regVia/`
  - `frontend/` — Vite + React 18 + TypeScript 5
  - `backend/` — Python 3.12, FastAPI, uv for dependency management
  - `infra/` — Terraform (AWS target), Dockerfiles
- Root `docker-compose.yml` services: `postgres`, `backend`, `frontend`
- `.gitignore` at root covering node_modules, `__pycache__`, `.env*`, `*.pyc`
- `.env.example` files in both `frontend/` and `backend/` listing every required env var (no values)

**Acceptance Criteria**
- [ ] `docker compose up` starts all services without errors
- [ ] `frontend/` TypeScript compiles with zero errors
- [ ] `backend/` FastAPI app boots and returns 200 on `GET /health`
- [ ] No secrets committed — `.env` files are gitignored

**Dependencies**
None

---

### ✅ REGVIA-002 · Configure frontend toolchain

**Problem Statement**
Frontend needs enforced code quality gates before any feature work begins.

**User Story**
As an engineer, I need lint, format, and type-check to run automatically on commit so the codebase stays consistent.

**Description**
Configure ESLint, Prettier, and TypeScript strict mode in the `frontend/` directory. Pre-commit enforcement is handled by the root-level `pre-commit` config (see REGVIA-003) — no Husky in the frontend.

**Technical Details**
- ESLint: `eslint-config-airbnb-typescript` + `eslint-plugin-react-hooks` + `eslint-plugin-jsx-a11y`
- Prettier: single quotes, 2-space indent, trailing commas ES5
- `tsconfig.json`: `strict: true`, `noUncheckedIndexedAccess: true`
- Path aliases: `@/` → `src/`
- Scripts: `pnpm lint` (`eslint . --max-warnings 0`), `pnpm type-check` (`tsc --noEmit`)

**Acceptance Criteria**
- [ ] `pnpm lint` exits 0 on clean code
- [ ] `pnpm type-check` exits 0
- [ ] Prettier formats on save (`.vscode/settings.json` included)

**Dependencies**
REGVIA-001

---

### ✅ REGVIA-003 · Configure backend toolchain + root pre-commit hooks

**Problem Statement**
Python projects without enforced formatting and type checking accumulate inconsistencies fast. In a monorepo, git hooks must live at the root — not inside a sub-directory — because there is only one `.git/`.

**User Story**
As an engineer, I need ruff, mypy, and pre-commit hooks covering both frontend and backend so the entire codebase is consistently typed and formatted on every commit.

**Description**
Configure `ruff` (lint + format) and `mypy` (strict) in `backend/`. Place a single `.pre-commit-config.yaml` at the **monorepo root** that enforces both backend (ruff, mypy) and frontend (eslint, tsc) quality gates.

**Technical Details**
- `ruff` replaces flake8 + isort + black; target Python 3.12
- `mypy`: `strict = true`, `ignore_missing_imports = true` for third-party stubs
- `pyproject.toml` defines all backend tool configs
- `uv` for dependency management (`uv.lock` committed)
- Root `.pre-commit-config.yaml` with `local` hooks:
  - `ruff-check`: `cd backend && uv run ruff check --fix` (files: `^backend/.*\.py$`)
  - `ruff-format`: `cd backend && uv run ruff format` (files: `^backend/.*\.py$`)
  - `mypy`: `cd backend && uv run mypy .` (files: `^backend/.*\.py$`)
  - `eslint`: `cd frontend && pnpm lint` (files: `^frontend/.*\.(ts|tsx)$`)
  - `tsc`: `cd frontend && pnpm type-check` (files: `^frontend/.*\.(ts|tsx)$`)
- Each hook is scoped by `files:` pattern so only relevant hooks fire per changed file

**Acceptance Criteria**
- [ ] `uv run ruff check .` exits 0 in `backend/`
- [ ] `uv run mypy .` exits 0 in `backend/`
- [ ] `pre-commit run --all-files` exits 0 from repo root
- [ ] Committing a `.py` file with a type error is blocked
- [ ] Committing a `.tsx` file with a TS error is blocked
- [ ] `uv run pytest` discovers tests in `backend/tests/`

**Dependencies**
REGVIA-001

---

## E1.5 — Test Infrastructure

> Set up before any feature work. Every engineer writing a feature ticket in E2–E11
> should be able to drop a test file alongside their code without any scaffolding friction.

---

### REGVIA-003A · Backend test infrastructure

**Problem Statement**
Without a test scaffold in place, tests get skipped during feature development and are bolted on at the end — the exact anti-pattern we're trying to avoid.

**User Story**
As a backend engineer, I need a ready-to-use pytest scaffold with async DB fixtures and a test client so I can write tests alongside every feature ticket without setup overhead.

**Description**
Create the full backend test scaffold: directory structure, `conftest.py` with reusable async fixtures, an async HTTP test client, and test utilities. No feature tests yet — just the infrastructure.

**Technical Details**

Directory structure:
```
backend/tests/
  conftest.py          # shared fixtures
  unit/
    __init__.py
  integration/
    __init__.py
```

`conftest.py` fixtures:
- `async_client` — `httpx.AsyncClient` wrapping the FastAPI app (function-scoped)
- `test_db` — async SQLAlchemy session pointed at a test database (function-scoped, rolls back after each test)
- `test_db_url` — reads `TEST_DATABASE_URL` env var, falls back to `DATABASE_URL` with `_test` suffix

`pyproject.toml` additions:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.coverage.report]
fail_under = 80
```

`.env.example` addition:
```
TEST_DATABASE_URL=postgresql+asyncpg://regvia:regvia@localhost:5432/regvia_test
```

**Acceptance Criteria**
- [ ] `uv run pytest` discovers `tests/unit/` and `tests/integration/` and exits 0 (no tests yet = pass)
- [ ] `async_client` fixture returns a working `AsyncClient` against the FastAPI app
- [ ] `test_db` fixture rolls back after each test (verified by checking no data persists between tests)
- [ ] A smoke test `test_health.py` passes: `GET /health` returns 200

**Dependencies**
REGVIA-003

---

### REGVIA-003B · Frontend test infrastructure

**Problem Statement**
Same problem as 003A — without a working test setup from the start, component tests never get written during feature development.

**User Story**
As a frontend engineer, I need Vitest + RTL + MSW configured with a custom render helper so I can write component tests alongside every feature ticket.

**Description**
Configure Vitest (replaces Jest — native Vite integration, faster), React Testing Library, and MSW for API mocking. Provide a custom `render` helper that wraps all providers (QueryClient, Router, etc.).

**Technical Details**

Packages to add to `frontend/`:
```
vitest, @vitest/coverage-v8, jsdom,
@testing-library/react, @testing-library/user-event, @testing-library/jest-dom,
msw
```

Files to create:
```
frontend/
  vitest.config.ts         # extends vite.config, sets jsdom environment
  src/
    test/
      setup.ts             # @testing-library/jest-dom matchers, MSW server lifecycle
      render.tsx           # custom render: wraps QueryClientProvider + MemoryRouter
      server.ts            # MSW server instance (used in setup.ts)
      handlers/
        index.ts           # barrel export for all MSW handlers
```

`vitest.config.ts`:
```typescript
import { defineConfig, mergeConfig } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(viteConfig, defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      thresholds: { lines: 80, functions: 80, branches: 70 },
    },
  },
}))
```

`package.json` script additions:
```json
"test": "vitest",
"test:coverage": "vitest run --coverage"
```

**Acceptance Criteria**
- [ ] `pnpm test` discovers test files and exits 0 (no tests yet = pass)
- [ ] `pnpm test:coverage` runs without error and reports coverage
- [ ] A smoke test `src/test/smoke.test.tsx` passes: renders a `<div>hello</div>` via custom render
- [ ] MSW server starts/stops cleanly in beforeAll/afterAll without console errors

**Dependencies**
REGVIA-002

---

## E2 — Database & Storage Layer

---

### REGVIA-004 · SQLAlchemy ORM models + Alembic migration + pgvector

**Problem Statement**
The RAG pipeline needs a durable, typed data layer. ORM models must be the single source of truth — migrations are autogenerated from them, not written by hand. Writing raw SQL migrations and then "mirroring" them into models is duplicate work that drifts.

**User Story**
As a backend engineer, I need SQLAlchemy async ORM models for all tables so I can write type-safe queries without raw SQL, and Alembic migrations autogenerated from those models so schema and code never diverge.

**Description**
Define all SQLAlchemy 2.x async ORM models, enable the pgvector extension, autogenerate the initial Alembic migration from the models, and add the HNSW index. The `summaries` table is included here (not deferred to E5) since the full schema is known upfront.

**Technical Details**

Model definitions (`backend/app/models/`):
```
app/models/
  __init__.py       # exports all models (required for Alembic autogenerate)
  base.py           # DeclarativeBase, common UUID primary key mixin, timestamp mixin
  document.py       # Document model
  chunk.py          # Chunk model
  embedding.py      # Embedding model
  chat_session.py   # ChatSession model
  message.py        # Message model
  summary.py        # Summary model
```

Key model details:
- `Base` from `sqlalchemy.orm.DeclarativeBase`
- UUID primary keys via `uuid.uuid4` default (not `gen_random_uuid()` — let SQLAlchemy own it)
- `DocumentStatus` — Python `enum.Enum` mapped to SQLAlchemy `Enum` type with `CHECK` constraint: `pending | processing | ready | failed`
- `MessageRole` — Python `enum.Enum`: `user | assistant`
- `Embedding.embedding` — `Vector(1536)` column via `pgvector.sqlalchemy`
- `Message.citations` — `JSONB` column (SQLAlchemy `JSON` type with `postgresql_using='jsonb'`)
- `updated_at` on `Document` and `Summary` uses `onupdate=func.now()`
- All relationships defined with `relationship()` + `back_populates` for bidirectional navigation

Schema (derived from models — do not write migrations by hand):
```
documents       → chunks (cascade delete)
                → chat_sessions (cascade delete)
                → summary (one-to-one, cascade delete)
chunks          → embeddings (cascade delete, one-to-one)
chat_sessions   → messages (cascade delete)
```

`summaries` table (included here, not in E5):
```python
class Summary(Base):
    id: UUID
    document_id: UUID  # FK → documents, unique, cascade delete
    obligations: list[dict]   # JSONB
    risks: list[dict]         # JSONB
    gaps: list[dict]          # JSONB
    recommendations: list[dict]  # JSONB
    generated_at: datetime
    created_at: datetime
```

Alembic setup (`backend/alembic/`):
- `alembic init` with async template (`asyncpg` dialect)
- `env.py`: imports `Base.metadata` from `app.models` so autogenerate sees all models
- Initial migration: `alembic revision --autogenerate -m "initial schema"`
- Post-autogenerate manual additions (not auto-detected):
  - `CREATE EXTENSION IF NOT EXISTS vector` (before table creation)
  - HNSW index: `CREATE INDEX ON embeddings USING hnsw (embedding vector_cosine_ops)`
- `alembic upgrade head` called in Docker entrypoint

Database session (`backend/app/db/session.py`):
```python
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

**Acceptance Criteria**
- [ ] `alembic upgrade head` runs without error on a fresh database
- [ ] `alembic downgrade -1` reverses the migration cleanly
- [ ] All models importable: `from app.models import Document, Chunk, Embedding, ChatSession, Message, Summary`
- [ ] `DocumentStatus` and `MessageRole` enums enforce values at the SQLAlchemy layer
- [ ] Deleting a `Document` cascades to chunks → embeddings, sessions → messages, summary
- [ ] pgvector `HNSW` index exists on `embeddings.embedding`
- [ ] Unit test: create a `Document` via ORM, assert it round-trips through `get_db()` session

**Dependencies**
REGVIA-003A

---

### REGVIA-004A · Model factories + seed layer

**Problem Statement**
Integration tests (REGVIA-003A) and E2E tests (REGVIA-023) both require realistic fixture data — documents with chunks and embeddings — without hitting S3 or OpenAI. Without a factory layer this becomes copy-paste fixture code spread across every test file.

**User Story**
As an engineer writing a test, I need a one-liner to create a realistic `Document` with chunks and embeddings in the test DB so I can focus on asserting behaviour, not constructing fixtures.

**Description**
Implement a Faker-based model factory layer used by both tests and the local dev seed script. Factories create ORM model instances and persist them via the async session from REGVIA-004.

**Technical Details**

`backend/tests/factories.py`:
```python
class DocumentFactory:
    @staticmethod
    async def create(session: AsyncSession, **kwargs) -> Document: ...

class ChunkFactory:
    @staticmethod
    async def create(session: AsyncSession, document: Document, **kwargs) -> Chunk: ...

class EmbeddingFactory:
    @staticmethod
    async def create(session: AsyncSession, chunk: Chunk, **kwargs) -> Embedding: ...

class ChatSessionFactory:
    @staticmethod
    async def create(session: AsyncSession, document: Document, **kwargs) -> ChatSession: ...
```

- Faker for realistic filenames, text content
- `EmbeddingFactory` generates a random `list[float]` of length 1536 (no OpenAI call)
- Factories accept `**kwargs` to override any field

`backend/scripts/seed.py` (local dev only, never runs in prod):
- Creates 1 sample document with 5 chunks + embeddings in `ready` status
- Run via `uv run python -m scripts.seed`

`conftest.py` additions (REGVIA-003A):
- `document_factory`, `chunk_factory` fixtures that yield factory classes with the `test_db` session pre-bound

**Acceptance Criteria**
- [ ] `DocumentFactory.create(session)` inserts a row and returns the ORM instance
- [ ] `ChunkFactory.create(session, document=doc)` correctly sets the FK
- [ ] `EmbeddingFactory.create(session, chunk=chunk)` produces a valid 1536-dim vector
- [ ] `uv run python -m scripts.seed` populates local dev DB without error
- [ ] Factory used in at least one integration test in `tests/integration/`

**Dependencies**
REGVIA-004

---

### REGVIA-005 · S3-compatible storage client (MinIO for local dev)

**Problem Statement**
PDFs must be stored outside the application server so the backend is stateless. For feature development (E3–E11), MinIO via docker-compose is a full drop-in for S3 — AWS provisioning is a deployment concern handled in E13.

**User Story**
As the system, I need a storage client abstraction backed by MinIO locally and S3 in production so feature code never changes between environments.

**Description**
Implement a `StorageClient` abstraction over boto3. Wire MinIO into docker-compose for local dev. AWS S3 + Terraform provisioning is deferred to REGVIA-026A in E13.

**Technical Details**

`backend/app/storage/client.py`:
```python
class StorageClient:
    async def upload(self, key: str, data: bytes, content_type: str) -> None: ...
    async def get_presigned_upload_url(self, key: str) -> str: ...
    async def get_presigned_download_url(self, key: str) -> str: ...
    async def delete(self, key: str) -> None: ...
```

- Backed by `boto3` (sync, run in threadpool via `asyncio.to_thread`)
- `endpoint_url` set from `S3_ENDPOINT_URL` env var — when set, points at MinIO; when unset, uses real AWS
- Single env var swap is the only difference between local and prod

`docker-compose.yml` additions:
```yaml
minio:
  image: minio/minio
  command: server /data --console-address ":9001"
  ports:
    - "9000:9000"
    - "9001:9001"
  environment:
    MINIO_ROOT_USER: regvia
    MINIO_ROOT_PASSWORD: regvia123
  volumes:
    - minio_data:/data
```

`.env.example` additions:
```
S3_ENDPOINT_URL=http://localhost:9000   # MinIO for local dev; unset for AWS
```

Bucket creation: a startup script/entrypoint creates the bucket in MinIO on first run if it doesn't exist (`mc mb` or boto3 `create_bucket`).

**Acceptance Criteria**
- [ ] `StorageClient.upload()` stores a file and `get_presigned_download_url()` returns a working URL against MinIO
- [ ] Switching `S3_ENDPOINT_URL` to empty points client at real AWS with no code changes
- [ ] MinIO console accessible at `http://localhost:9001` after `docker compose up`
- [ ] Unit test: mock boto3, assert `upload` calls `put_object` with correct key and content-type

**Dependencies**
REGVIA-001

---

## E3 — Document Upload & Processing

---

### REGVIA-006 · POST /api/v1/documents — upload endpoint

**Problem Statement**
Users need a way to submit PDFs to the system. The API must accept the file, validate it, store it in S3, and create a database record before returning.

**User Story**
As a user uploading a PDF, I want a fast response confirming my document was received, even if processing takes longer.

**Description**
Implement the upload endpoint. It returns a document ID immediately; processing is enqueued as a background task (REGVIA-007).

**Technical Details**

Request:
```
POST /api/v1/documents
Content-Type: multipart/form-data
Body: file (PDF, max 50MB)
```

Response:
```json
{
  "data": {
    "document_id": "uuid",
    "filename": "gdpr-policy.pdf",
    "status": "pending",
    "created_at": "ISO8601"
  },
  "error": null
}
```

Validation (Pydantic):
- MIME type must be `application/pdf`
- File size ≤ 50MB
- Filename sanitized (alphanumeric, hyphens, underscores, dot-pdf only)

Processing:
1. Validate file
2. Generate `s3_key = f"documents/{document_id}/{sanitized_filename}"`
3. Upload to S3
4. Insert `documents` row with `status = 'pending'`
5. Enqueue background processing task (FastAPI `BackgroundTasks`)
6. Return 202 with document record

Error codes:
- `INVALID_FILE_TYPE` — not a PDF
- `FILE_TOO_LARGE` — exceeds 50MB
- `UPLOAD_FAILED` — S3 error

**Acceptance Criteria**
- [ ] Returns 202 within 2s for a 10MB PDF
- [ ] Document row created in DB with `status = 'pending'`
- [ ] PDF stored at correct S3 key
- [ ] Rejects non-PDF with 422 and `INVALID_FILE_TYPE` error code
- [ ] Rejects files > 50MB with 413

**Dependencies**
REGVIA-004, REGVIA-005

---

### REGVIA-007 · Background PDF processing pipeline

**Problem Statement**
Parsing a PDF, chunking text, and generating embeddings takes 10–60 seconds — far too long for a synchronous HTTP response.

**User Story**
As a user, I want the system to process my document in the background so I can see a progress indicator rather than a stalled request.

**Description**
Implement the async processing pipeline that runs after upload. Updates `document.status` as it progresses so the frontend can poll for completion.

**Technical Details**

Pipeline steps (executed in order, each wrapped in try/except that sets `status = 'failed'` on error):

**Step 1 — Extract text**
- Library: `pdfplumber` (better table/layout handling than pypdf)
- Extract text per page, preserve page numbers
- Skip pages with < 20 characters (blank/image-only)

**Step 2 — Chunking**
- Strategy: semantic chunking with fixed-size fallback
- Chunk size: 512 tokens (measured via `tiktoken cl100k_base`)
- Overlap: 50 tokens (preserves context across chunk boundaries)
- Each chunk records: `document_id`, `chunk_index`, `page_number`, `text`, `token_count`
- Minimum chunk size: 100 tokens (discard smaller)

**Step 3 — Embedding**
- Model: `text-embedding-3-small` (1536 dims, cost-effective)
- Batch size: 100 chunks per API call
- Store each embedding in `embeddings` table linked to its chunk

**Step 4 — Status update**
- Set `document.status = 'ready'`
- Set `document.updated_at = NOW()`

Status transitions: `pending` → `processing` → `ready` | `failed`

**Acceptance Criteria**
- [ ] A 20-page PDF reaches `status = 'ready'` within 60s
- [ ] Chunk count is ≥ 1 and each chunk has a corresponding embedding
- [ ] Page numbers are preserved and correct
- [ ] Processing failure sets `status = 'failed'` with structured log entry
- [ ] Re-triggering processing on an already-`ready` document is a no-op (idempotent)

**Dependencies**
REGVIA-006

---

### REGVIA-008 · GET /api/v1/documents/{id} — status polling endpoint

**Problem Statement**
The frontend needs to know when processing is complete to enable the chat and summary features.

**User Story**
As a user waiting for my document to process, I want to poll the status so the UI can show a progress state.

**Description**
Lightweight read endpoint that returns current document status and metadata.

**Technical Details**

Response:
```json
{
  "data": {
    "document_id": "uuid",
    "filename": "gdpr-policy.pdf",
    "status": "ready",
    "chunk_count": 84,
    "created_at": "ISO8601",
    "updated_at": "ISO8601"
  },
  "error": null
}
```

- `chunk_count` is a COUNT query on `chunks` table (cached on `document` row after processing)
- Returns 404 with `DOCUMENT_NOT_FOUND` if ID does not exist

**Acceptance Criteria**
- [ ] Returns correct `status` at each pipeline stage
- [ ] `chunk_count` matches actual chunk rows
- [ ] 404 on unknown ID
- [ ] Response time < 50ms (single indexed lookup)

**Dependencies**
REGVIA-007

---

## E4 — RAG Pipeline

---

### REGVIA-009 · Retrieval service — semantic search over chunks

**Problem Statement**
The RAG pipeline needs to find the most semantically relevant document chunks for any user question before sending them to the LLM.

**User Story**
As the AI system, I need to retrieve the top-k most relevant chunks for a query so I can ground my response in the document.

**Description**
Implement a retrieval service that embeds the query and runs cosine similarity search against pgvector.

**Technical Details**

```python
class RetrievalService:
    async def retrieve(
        self,
        query: str,
        document_id: UUID,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        ...
```

Algorithm:
1. Embed query using `text-embedding-3-small` (same model as indexing — must match)
2. pgvector query:
   ```sql
   SELECT c.id, c.text, c.page_number, c.chunk_index,
          1 - (e.embedding <=> $query_vec) AS similarity
   FROM embeddings e
   JOIN chunks c ON c.id = e.chunk_id
   WHERE c.document_id = $document_id
   ORDER BY e.embedding <=> $query_vec
   LIMIT $top_k;
   ```
3. Filter results with `similarity < 0.3` (low relevance threshold — discard noise)
4. Return `RetrievedChunk(chunk_id, text, page_number, similarity)`

`RetrievedChunk` is a Pydantic model — no raw dicts.

**Acceptance Criteria**
- [ ] Returns top-5 chunks ordered by descending similarity
- [ ] Chunks with similarity < 0.3 are excluded
- [ ] Results are scoped to the specified `document_id` only
- [ ] Unit test: mock embedding + mock DB, assert ordering and filtering
- [ ] Latency < 200ms for 10k embeddings (pgvector HNSW)

**Dependencies**
REGVIA-007

---

### REGVIA-010 · POST /api/v1/chat — Q&A with citations

**Problem Statement**
Users need to ask questions about their document and receive grounded answers with source citations.

**User Story**
As a user, I want to ask a question about my compliance document and get an accurate answer that cites specific pages, so I can verify the information myself.

**Description**
Implement the chat endpoint. It retrieves relevant chunks, constructs a grounded prompt, generates a response via OpenAI, and returns the answer with citations. Supports streaming (SSE) as a bonus.

**Technical Details**

Request:
```json
{
  "document_id": "uuid",
  "session_id": "uuid | null",
  "question": "What are the data retention requirements?"
}
```

Response (non-streaming):
```json
{
  "data": {
    "session_id": "uuid",
    "message_id": "uuid",
    "answer": "According to Section 4.2, data must be retained for...",
    "citations": [
      {
        "chunk_id": "uuid",
        "page_number": 7,
        "excerpt": "...data shall be retained for a minimum period of 5 years..."
      }
    ],
    "found_in_document": true
  },
  "error": null
}
```

Prompt design (system prompt, non-negotiable):
```
You are a compliance assistant. Answer the user's question using ONLY the
context provided below. If the answer is not present in the context, respond
with exactly: "I could not find this information in the document."
Do not infer, extrapolate, or use outside knowledge.
For each claim you make, indicate the source chunk ID in square brackets, e.g. [chunk:uuid].

Context:
{retrieved_chunks_with_ids}
```

Citation extraction:
- Parse `[chunk:uuid]` markers from LLM output
- Map back to `{chunk_id, page_number, excerpt}` from retrieved chunks
- Strip markers from the final answer shown to users

`found_in_document`:
- `false` if answer equals the "not found" sentinel string
- `true` otherwise

LangSmith tracing:
- Wrap entire chain in `@traceable` decorator
- Tag with `document_id`, `session_id`, `question`

**Acceptance Criteria**
- [ ] Returns grounded answer with ≥ 1 citation when relevant chunk exists
- [ ] Returns `found_in_document: false` and the sentinel message when no chunk is relevant
- [ ] LangSmith trace visible for each call with correct tags
- [ ] Answer never contains `[chunk:uuid]` markers in the user-visible text
- [ ] Creates `chat_sessions` and `messages` rows
- [ ] Unit test: mock retrieval + mock OpenAI, assert citation extraction logic

**Dependencies**
REGVIA-009

---

### REGVIA-011 · Streaming chat via SSE

**Problem Statement**
LLM responses take 3–10 seconds. Non-streaming creates a dead UI; streaming makes the product feel alive.

**User Story**
As a user, I want to see the answer appearing word-by-word so the interface feels responsive.

**Description**
Add a streaming variant of the chat endpoint using Server-Sent Events. The frontend renders tokens incrementally.

**Technical Details**

Endpoint: `POST /api/v1/chat/stream`
- Returns `Content-Type: text/event-stream`
- Event types:
  - `event: token\ndata: {"token": "..."}\n\n` — each streamed token
  - `event: citations\ndata: {"citations": [...]}\n\n` — sent after stream ends
  - `event: done\ndata: {}\n\n` — signals completion
  - `event: error\ndata: {"message": "...", "code": "..."}\n\n` — on error

Implementation:
- Use `openai.AsyncOpenAI` with `stream=True`
- Collect full response in background to extract citations, then emit `citations` event
- FastAPI `StreamingResponse` with generator

Frontend:
- Use native `EventSource` API or `fetch` with `ReadableStream`
- Append tokens to message bubble as they arrive
- Render citations panel after `citations` event

**Acceptance Criteria**
- [ ] First token appears within 1s of request
- [ ] Citations are emitted after stream completes
- [ ] Client-side: tokens render incrementally without re-renders of entire message list
- [ ] `error` event sent (not HTTP error) if LLM call fails mid-stream
- [ ] Graceful degradation: if `EventSource` not supported, falls back to non-streaming endpoint

**Dependencies**
REGVIA-010

---

## E5 — Compliance Summary

---

### REGVIA-012 · POST /api/v1/documents/{id}/summary — generate compliance summary

**Problem Statement**
Users need a structured compliance overview of their document without having to ask individual questions.

**User Story**
As a compliance analyst, I want the system to automatically extract obligations, risks, gaps, and recommendations from my document so I can review compliance posture at a glance.

**Description**
Implement the summary generation endpoint. It retrieves all chunks (or a scored sample for large documents), runs a structured extraction prompt, and returns a typed summary.

**Technical Details**

Response schema (Pydantic + JSON):
```json
{
  "data": {
    "document_id": "uuid",
    "obligations": [
      {"text": "...", "page_number": 3, "chunk_id": "uuid"}
    ],
    "risks": [
      {"text": "...", "severity": "high|medium|low", "page_number": 5, "chunk_id": "uuid"}
    ],
    "gaps": [
      {"text": "...", "page_number": null, "chunk_id": null}
    ],
    "recommendations": [
      {"text": "...", "priority": "high|medium|low"}
    ],
    "generated_at": "ISO8601"
  },
  "error": null
}
```

Prompt strategy:
- For documents ≤ 30 chunks: pass all chunks in a single prompt
- For documents > 30 chunks: use map-reduce — summarize per-chunk, then synthesize
- Use OpenAI function calling / structured output to enforce schema (no free-text parsing)
- Model: `gpt-4o-mini` for cost efficiency; `gpt-4o` configurable via env var

LangSmith:
- Trace tagged with `document_id`, `strategy` (direct|map-reduce), `chunk_count`

Caching:
- Store result in a `summaries` table (add migration) keyed by `document_id`
- Return cached result if exists; bust cache if document is re-processed

**Acceptance Criteria**
- [ ] Returns structured JSON matching schema exactly (enforced by Pydantic)
- [ ] `obligations`, `risks`, `gaps`, `recommendations` are all non-empty arrays for a real compliance PDF
- [ ] LangSmith trace shows map-reduce strategy for docs > 30 chunks
- [ ] Second call returns cached result without calling OpenAI
- [ ] Unit test: mock OpenAI structured output, assert schema validation

**Dependencies**
REGVIA-007

---

## E6 — Streaming & Background Jobs

> REGVIA-011 covers streaming. This epic covers job infrastructure if needed for scale.

---

### REGVIA-013 · Background task queue (Celery + Redis) — optional scale path

**Problem Statement**
FastAPI `BackgroundTasks` is in-process and dies if the server restarts mid-processing. For reliability, processing must survive restarts.

**User Story**
As an operator, I need document processing to be durable so a server restart doesn't leave documents permanently stuck in `processing`.

**Description**
Replace `BackgroundTasks` with Celery workers backed by Redis. This is the production path; local dev can still use `BackgroundTasks` via feature flag.

**Technical Details**
- Celery with Redis broker
- Task: `process_document(document_id: str)` — idempotent (checks current status before running)
- Worker runs as separate Docker service
- Dead letter queue: failed tasks after 3 retries move to `failed` queue, document status set to `failed`
- Flower (Celery monitoring) at `/flower` in dev

Feature flag: `USE_CELERY=true/false` env var — when false, uses FastAPI BackgroundTasks

**Acceptance Criteria**
- [ ] Server restart during processing: task resumes on worker restart
- [ ] Failed task (e.g. OpenAI error): retried 3x, then document status = `failed`
- [ ] `USE_CELERY=false` path works identically for local dev
- [ ] Flower dashboard shows task state

**Dependencies**
REGVIA-007

---

## E7 — Observability & Logging

---

### REGVIA-014 · Structured logging with Loguru + OpenTelemetry

**Problem Statement**
Unstructured print statements make debugging in production impossible. Every request and AI call must be traceable.

**User Story**
As an operator, I need structured logs and distributed traces so I can diagnose issues without SSH-ing into servers.

**Description**
Configure Loguru for structured JSON logging and OpenTelemetry for distributed tracing across all backend services.

**Technical Details**
- Loguru: output format `{"timestamp": ..., "level": ..., "message": ..., "extra": {...}}`
- Every log entry includes: `request_id` (injected by middleware), `document_id` (when applicable)
- Request middleware: generate UUID `request_id`, inject into log context
- OpenTelemetry: instrument FastAPI + SQLAlchemy + httpx (OpenAI client)
- Export: OTLP to local Jaeger in dev, AWS X-Ray in prod
- Log levels: `DEBUG` in dev, `INFO` in prod (env-controlled)

**Acceptance Criteria**
- [ ] Every HTTP request produces a structured log line with `request_id`, `method`, `path`, `status_code`, `duration_ms`
- [ ] Every OpenAI call produces a log line with `model`, `prompt_tokens`, `completion_tokens`, `latency_ms`
- [ ] Jaeger UI shows complete trace for a chat request spanning FastAPI → pgvector → OpenAI
- [ ] No `print()` statements in the codebase

**Dependencies**
REGVIA-003

---

### REGVIA-015 · LangSmith integration for LLM observability

**Problem Statement**
We need to evaluate and debug LLM calls in production. LangSmith provides the trace visibility and eval framework needed.

**User Story**
As an AI engineer, I need every LLM call traced in LangSmith so I can evaluate answer quality, catch regressions, and debug hallucinations.

**Description**
Integrate LangSmith tracing for all LLM calls in the RAG pipeline and summary generation. Implement a basic eval dataset.

**Technical Details**
- Set `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT=regvia-copilot`
- All LLM chains wrapped with `@traceable` or run through LangChain LCEL (auto-traced)
- Trace metadata: `document_id`, `session_id`, `chunk_count`, `strategy`
- Eval dataset: 5 question-answer pairs from a sample compliance PDF stored in LangSmith
- Run evals on CI: `langsmith evaluate` compares against golden answers using LLM-as-judge
- LangSmith dataset name: `regvia-rag-evals`

**Acceptance Criteria**
- [ ] LangSmith project `regvia-copilot` shows traces for every `/api/v1/chat` call
- [ ] Trace includes retrieved chunks, prompt, and completion
- [ ] Eval run passes ≥ 80% on golden dataset
- [ ] `LANGCHAIN_TRACING_V2=false` disables tracing without breaking functionality

**Dependencies**
REGVIA-010, REGVIA-012

---

## E8 — Frontend Foundation

---

### REGVIA-016 · Frontend project scaffold — Atomic Design structure

**Problem Statement**
Without an enforced structure, React projects sprawl into unmaintainable component soup.

**User Story**
As a frontend engineer, I need the project scaffolded with Atomic Design and all libraries installed so I can build features without setup friction.

**Description**
Create the `frontend/` project with all required dependencies and the full Atomic Design directory structure.

**Technical Details**

Directory structure:
```
src/
  components/
    atoms/          # Button, Input, Badge, Spinner, Label, Icon
    molecules/      # FormField, FileDropzone, StatusBadge, CitationCard
    organisms/      # UploadPanel, ChatBox, SummaryPanel, MessageList
    templates/      # AppLayout, TwoColumnLayout
    pages/          # UploadPage, ChatPage (thin — composition only)
  features/
    document/       # useDocumentUpload, useDocumentStatus hooks
    chat/           # useChatSession, useSendMessage hooks
    summary/        # useSummary hook
  shared/
    hooks/          # useSSE, useDebounce
    utils/          # formatDate, truncateText
    types/          # Document, Message, Citation, Summary (Zod schemas + inferred TS types)
    api/            # axios instance, API functions
  store/            # Zustand stores (UI state only)
  router/           # React Router routes
```

Libraries:
- React 18 + TypeScript 5
- Tailwind CSS 3 + shadcn/ui
- TanStack Query v5 (server state)
- Zustand v4 (UI state)
- React Hook Form v7 + Zod v3
- React Router v6
- Axios (API client)
- `EventSource` polyfill for SSE

State rules (enforced in code review):
- TanStack Query: all server data (documents, messages, summaries)
- Zustand: sidebar open/close, active tab, upload modal visibility
- No `useState` for server data

**Acceptance Criteria**
- [ ] All directories exist with index barrel exports
- [ ] `pnpm dev` starts without errors
- [ ] shadcn/ui `Button` component renders in a smoke test
- [ ] TanStack Query DevTools visible in dev mode
- [ ] Zustand store accessible and typed

**Dependencies**
REGVIA-002

---

### REGVIA-017 · API client layer + Zod schemas

**Problem Statement**
Without typed API contracts on the frontend, backend changes cause silent runtime failures.

**User Story**
As a frontend engineer, I need a typed API client where every response is validated against a Zod schema so I catch contract violations immediately.

**Description**
Implement the axios-based API client with Zod schema validation on every response. Define schemas mirroring all backend Pydantic models.

**Technical Details**

Schemas (`src/shared/types/`):

```typescript
const DocumentSchema = z.object({
  document_id: z.string().uuid(),
  filename: z.string(),
  status: z.enum(['pending', 'processing', 'ready', 'failed']),
  chunk_count: z.number().optional(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
})

const CitationSchema = z.object({
  chunk_id: z.string().uuid(),
  page_number: z.number(),
  excerpt: z.string(),
})

const MessageSchema = z.object({
  session_id: z.string().uuid(),
  message_id: z.string().uuid(),
  answer: z.string(),
  citations: z.array(CitationSchema),
  found_in_document: z.boolean(),
})

const ApiResponseSchema = <T extends z.ZodTypeAny>(data: T) =>
  z.object({ data: data, error: z.union([z.null(), z.object({ message: z.string(), code: z.string() })]) })
```

API functions:
```typescript
export const uploadDocument = (file: File): Promise<Document>
export const getDocumentStatus = (id: string): Promise<Document>
export const sendMessage = (req: ChatRequest): Promise<Message>
export const getSummary = (documentId: string): Promise<Summary>
```

- All functions parse response through Zod; throw `ApiValidationError` on mismatch
- Axios interceptor: if `response.data.error !== null`, throw `ApiError` with `message` and `code`
- Base URL from `VITE_API_BASE_URL` env var

**Acceptance Criteria**
- [ ] TypeScript infers correct return types from Zod schemas (no `any`)
- [ ] Passing a malformed API response to a schema throws at runtime
- [ ] All API functions are unit-tested with MSW mocks
- [ ] `ApiError` is caught by TanStack Query and surfaces in `error` state

**Dependencies**
REGVIA-016

---

## E9 — Document Feature (Upload UI)

---

### REGVIA-018 · Upload page — drag-and-drop PDF upload with status polling

**Problem Statement**
Users need a clear, guided path to upload a PDF and know when it's ready to use.

**User Story**
As a user, I want to drag-and-drop my PDF and see a progress indicator while it's being processed, so I know when I can start asking questions.

**Description**
Build the Upload page using Atomic Design components. The page handles file selection, upload, and polls for processing status.

**Technical Details**

Component hierarchy:
```
UploadPage (pages/)
  └── AppLayout (templates/)
       └── UploadPanel (organisms/)
            ├── FileDropzone (molecules/)  ← drag-drop + file input atom
            ├── UploadProgress (molecules/) ← progress bar atom + status text
            └── ProcessingStatus (molecules/) ← status badge + description
```

Behaviour:
1. User drags PDF onto `FileDropzone` or clicks to browse
2. RHF + Zod validate: type = PDF, size ≤ 50MB
3. On submit: call `uploadDocument()` → receive `document_id`
4. Navigate to `/chat/:document_id` — polling begins in `useDocumentStatus`
5. TanStack Query polls `GET /documents/:id` every 2s while `status !== 'ready' | 'failed'`
6. On `ready`: enable chat + summary tabs
7. On `failed`: show error state with retry button

State:
- Zustand: `uploadModalOpen` (if modal variant is chosen)
- TanStack Query: `useDocumentStatus(documentId)` with `refetchInterval`

Atoms used: `Button`, `Input`, `Spinner`, `Badge`
Molecules used: `FileDropzone`, `StatusBadge`
No business logic in atoms or molecules.

**Acceptance Criteria**
- [ ] Drag-drop works in Chrome, Firefox, Safari
- [ ] File > 50MB shows inline validation error without attempting upload
- [ ] Non-PDF file shows "Only PDF files are supported" error
- [ ] Processing spinner visible while `status === 'processing'`
- [ ] Auto-navigates to chat when `status === 'ready'`
- [ ] Failed state shows actionable error message + retry

**Dependencies**
REGVIA-017, REGVIA-008

---

## E10 — Chat Feature (Q&A UI)

---

### REGVIA-019 · Chat interface with citation rendering

**Problem Statement**
The core product value is conversational Q&A over a document. The UI must feel fast, show citations clearly, and handle the "not found" case without confusion.

**User Story**
As a user, I want to type a question, see the answer stream in, and then see which pages the answer came from, so I can trust and verify the response.

**Description**
Build the chat interface with streaming support and citation display.

**Technical Details**

Component hierarchy:
```
ChatPage (pages/)
  └── TwoColumnLayout (templates/)
       ├── [left] MessageList (organisms/)
       │         └── MessageBubble (molecules/) × N
       │              ├── [text] answer text (atom: Text)
       │              └── [citations] CitationCard (molecules/) × N
       └── [right] ChatInputBar (organisms/)
                  ├── Input (atom)
                  └── Button (atom) — Send
```

Streaming behaviour:
1. User submits question
2. Open SSE connection to `/api/v1/chat/stream`
3. Append streaming tokens to a "pending" message bubble
4. On `citations` event: render `CitationCard` components below answer
5. On `done`: mark message complete, enable input
6. On `error`: show error state in message bubble, re-enable input

Non-streaming fallback: if SSE not available, use `sendMessage()` and render full answer at once.

CitationCard shows:
- Page number
- Excerpt (first 120 chars, truncated with "…")
- Click → scrolls to/highlights chunk (stretch goal)

"Not found" state:
- `found_in_document: false` → render message with distinct styling (grey, italic)
- Text: "I could not find this information in the document."
- No citation cards rendered

Zustand state:
- `activeSessionId: string | null`
- `streamingMessageId: string | null`

TanStack Query:
- `useQuery` for message history (on session load)
- `useMutation` for sending messages (non-streaming)

**Acceptance Criteria**
- [ ] Streaming tokens appear incrementally (< 100ms between visible token groups)
- [ ] Citations rendered after stream completes
- [ ] "Not found" case has distinct visual treatment
- [ ] Input disabled while streaming, re-enabled on completion
- [ ] Message history persists across page refresh (loaded from backend)
- [ ] RTL tests: message renders, citation card renders, "not found" renders

**Dependencies**
REGVIA-011, REGVIA-017

---

## E11 — Summary Feature (Summary UI)

---

### REGVIA-020 · Compliance summary view

**Problem Statement**
Users need a high-level view of obligations, risks, gaps, and recommendations without asking individual questions.

**User Story**
As a compliance analyst, I want to see a structured summary panel so I can quickly assess the compliance posture of my document.

**Description**
Build the summary tab/panel that triggers summary generation and renders the structured result.

**Technical Details**

Component hierarchy:
```
SummaryPanel (organisms/)
  ├── SummarySection (molecules/) × 4
  │    ├── SectionHeader (atom: heading + icon)
  │    └── SummaryItem (molecules/) × N
  │         ├── ItemText (atom)
  │         ├── SeverityBadge (atom) — for risks/recommendations
  │         └── PageRef (atom) — "p.7" chip linking to citation
  └── GenerateSummaryButton (molecule) — visible if no summary cached
```

Behaviour:
1. On entering summary tab: check if summary exists via `useQuery`
2. If no summary: show "Generate Summary" button
3. Button click: `useMutation` → `POST /documents/:id/summary`
4. Loading state: skeleton placeholders for each section
5. Render 4 sections: Obligations, Risks, Gaps, Recommendations
6. Risk/recommendation items show severity badge (`high` = red, `medium` = amber, `low` = green)

**Acceptance Criteria**
- [ ] Summary loads from cache on second visit (no extra API call)
- [ ] All 4 sections rendered with correct data
- [ ] Severity badges use correct colors
- [ ] Skeleton loaders shown during generation
- [ ] RTL test: renders all sections, severity badge colors, loading state

**Dependencies**
REGVIA-012, REGVIA-017

---

## E12 — Testing (Feature Tests)

> Test infrastructure is set up in E1.5 (REGVIA-003A/B). By the time these tickets are reached,
> each feature ticket in E2–E11 should already have unit tests written alongside it.
> E12 focuses on integration tests, coverage audits, and filling any gaps.

---

### REGVIA-021 · Backend integration tests + coverage gate

**Problem Statement**
Unit tests written per-feature need integration-level validation across the full pipeline. Coverage must be audited and enforced before CI is wired.

**User Story**
As an engineer, I need integration tests covering the full upload → process → query pipeline so cross-component regressions are caught before deployment.

**Description**
Write integration tests that exercise the full request path against a real database. Audit coverage and fill any gaps to meet the 80% threshold. Test infrastructure (conftest, fixtures, async client) is already in place from REGVIA-003A.

**Technical Details**
- All tests use fixtures from `conftest.py` (REGVIA-003A) — no new framework setup
- Mocking: `pytest-mock` for OpenAI/S3 only; never mock the database
- Coverage target: lines ≥ 80%, functions ≥ 80%, branches ≥ 70%

Integration tests (`tests/integration/`):
- `test_upload_endpoint.py`: upload → DB row created → S3 object exists
- `test_processing_pipeline.py`: full pipeline run with mocked OpenAI embeddings, real DB chunks/embeddings
- `test_chat_endpoint.py`: full RAG call with mocked OpenAI chat, real DB retrieval
- `test_summary_endpoint.py`: map-reduce path triggered for docs > 30 chunks

Unit test audit (`tests/unit/`) — fill gaps if not written during feature tickets:
- `test_chunking.py`: chunk size, overlap, min-size filter
- `test_citation_extraction.py`: `[chunk:uuid]` marker parsing
- `test_retrieval_filter.py`: similarity threshold filtering
- `test_schemas.py`: Pydantic validation edge cases

**Acceptance Criteria**
- [ ] `uv run pytest --cov` reports ≥ 80% line coverage
- [ ] All unit tests run without any network calls (fully mocked)
- [ ] Integration tests run against real PostgreSQL (Docker)
- [ ] CI fails if coverage drops below threshold

**Dependencies**
REGVIA-003A, REGVIA-010, REGVIA-012

---

### REGVIA-022 · Frontend integration tests + coverage gate

**Problem Statement**
Component tests written per-feature need a coverage audit and integration-level tests for cross-component flows before CI is wired.

**User Story**
As an engineer, I need end-to-end component integration tests and a coverage gate so UI regressions are caught in CI.

**Description**
Write integration-level component tests that exercise full user flows (upload → poll → chat). Audit coverage and fill any gaps. Test infrastructure (Vitest, RTL, MSW, custom render) is already in place from REGVIA-003B.

**Technical Details**
- All tests use the custom `render` helper from REGVIA-003B — no new framework setup
- MSW handlers cover all API endpoints
- Coverage: lines ≥ 80%, functions ≥ 80%, branches ≥ 70%
- Test files colocated: `Component.test.tsx` next to `Component.tsx`

Required tests (fill gaps if not written during feature tickets):
- `UploadPanel.test.tsx`: file validation, upload success/error states
- `ChatBox.test.tsx`: message rendering, streaming simulation, citation display
- `SummaryPanel.test.tsx`: section rendering, loading state, severity badges
- `useDocumentStatus.test.ts`: polling interval, stops on ready/failed
- `useSendMessage.test.ts`: mutation states, error handling

**Acceptance Criteria**
- [ ] `pnpm test:coverage` reports ≥ 80% line coverage
- [ ] MSW intercepts all API calls (no real network in tests)
- [ ] All component tests render without console errors
- [ ] CI fails if coverage drops below threshold

**Dependencies**
REGVIA-003B, REGVIA-018, REGVIA-019, REGVIA-020

---

### REGVIA-023 · E2E tests (Playwright)

**Problem Statement**
Unit tests cannot catch integration failures across the full user journey.

**User Story**
As a QA engineer, I need E2E tests covering the three critical flows so deployment regressions are caught before users see them.

**Description**
Implement Playwright E2E tests for the three primary user journeys.

**Technical Details**
- Playwright with TypeScript
- Tests run against local Docker stack (`docker compose up`)
- Test fixture: pre-seeded test document in DB + S3

Test suites:
1. **Upload flow** (`upload.spec.ts`)
   - Navigate to upload page
   - Drop a sample PDF
   - Assert status transitions: pending → processing → ready
   - Assert redirect to chat page

2. **Chat flow** (`chat.spec.ts`)
   - Ask a question with a known answer in the test PDF
   - Assert answer appears (streaming)
   - Assert ≥ 1 citation rendered
   - Ask a question with no answer → assert "not found" message

3. **Summary flow** (`summary.spec.ts`)
   - Click "Generate Summary"
   - Assert all 4 sections appear with content
   - Reload page → assert summary loads from cache (no loading state)

**Acceptance Criteria**
- [ ] All 3 suites pass against local Docker stack
- [ ] Playwright HTML report generated on CI
- [ ] Tests are deterministic (no flakiness from timing)

**Dependencies**
REGVIA-018, REGVIA-019, REGVIA-020

---

## E13 — Deployment & CI/CD

---

### REGVIA-024 · Dockerize all services

**Problem Statement**
Without containerization, "it works on my machine" is the only guarantee.

**User Story**
As an operator, I need all services to run identically in dev and production via Docker so deployments are reproducible.

**Description**
Create production-grade Dockerfiles for frontend and backend. Update docker-compose for local dev.

**Technical Details**

`backend/Dockerfile`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`frontend/Dockerfile` (multi-stage):
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

`docker-compose.yml` services: `postgres` (pgvector image), `redis`, `backend`, `worker` (Celery), `frontend`, `minio`, `jaeger`

Secrets: all via environment variables, never baked into images.

**Acceptance Criteria**
- [ ] `docker compose up --build` starts entire stack from scratch
- [ ] Frontend production build served correctly via nginx
- [ ] No secrets in Dockerfile or docker-compose (only references to env vars)
- [ ] Images are < 500MB

**Dependencies**
REGVIA-013, REGVIA-016

---

### REGVIA-025 · GitHub Actions CI pipeline

**Problem Statement**
Without CI, broken code reaches main and blocks the team.

**User Story**
As an engineer, I need CI to run lint, type-check, tests, and build on every pull request so main stays green.

**Description**
Implement GitHub Actions workflows for both frontend and backend.

**Technical Details**

`.github/workflows/ci.yml`:

Jobs (run in parallel):
1. `backend-ci`:
   - Python 3.12
   - `uv sync`
   - `ruff check .`
   - `mypy .`
   - `pytest --cov --cov-fail-under=80`
   - Services: `postgres:16-pgvector`, `redis`

2. `frontend-ci`:
   - Node 20
   - `pnpm install --frozen-lockfile`
   - `pnpm lint`
   - `pnpm type-check`
   - `pnpm test --coverage`
   - `pnpm build`

3. `e2e` (runs after both pass):
   - `docker compose up -d`
   - `pnpm playwright test`
   - Upload Playwright HTML report as artifact

Secrets stored in GitHub repository secrets, never in workflow files.

**Acceptance Criteria**
- [ ] CI runs on every PR to `main`
- [ ] All 3 jobs must pass before merge is allowed (branch protection)
- [ ] CI time < 10 minutes end-to-end
- [ ] Coverage reports uploaded as artifacts

**Dependencies**
REGVIA-021, REGVIA-022, REGVIA-023, REGVIA-024

---

### REGVIA-026A · Terraform AWS S3 bucket + IAM (extracted from REGVIA-005)

**Problem Statement**
The production deployment needs a real S3 bucket with least-privilege IAM access. This is a deployment concern — feature code uses the `StorageClient` abstraction from REGVIA-005 and is already tested against MinIO; this ticket only provisions the AWS-side resources.

**User Story**
As an operator, I need an S3 bucket provisioned via Terraform with correct IAM policies so the production backend can store and retrieve PDFs without overly broad permissions.

**Description**
Provision the S3 bucket and IAM policy in Terraform. No application code changes — the `StorageClient` from REGVIA-005 already handles both MinIO and S3 via `S3_ENDPOINT_URL`.

**Technical Details**
- `aws_s3_bucket`: versioning enabled, SSE-S3 encryption, public access blocked
- `aws_iam_policy`: `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` scoped to bucket ARN only — no `s3:ListBucket`
- `aws_iam_role_policy_attachment`: attach policy to ECS task role (defined in REGVIA-026)
- Bucket name from Terraform variable, injected as `S3_BUCKET_NAME` env var via ECS task definition

**Acceptance Criteria**
- [ ] `terraform plan` shows bucket + IAM policy with no drift
- [ ] ECS task role cannot `ListBucket` (IAM enforced)
- [ ] File uploaded via presigned URL is retrievable in production
- [ ] No bucket name or ARN hardcoded — all via Terraform variables

**Dependencies**
REGVIA-005, REGVIA-025

---

### REGVIA-026 · AWS deployment (ECS Fargate + RDS + ElastiCache)

**Problem Statement**
The application needs to run on a publicly accessible URL with production-grade reliability.

**User Story**
As a user and evaluator, I need the application running at a public URL so I can access it without local setup.

**Description**
Deploy all services to AWS using Terraform. Target: ECS Fargate for containers, RDS PostgreSQL + pgvector for database, ElastiCache Redis for task queue, S3 for PDFs, CloudFront for frontend.

**Technical Details**

Terraform resources (`infra/`):
- `aws_ecs_cluster` + `aws_ecs_task_definition` for backend + worker
- `aws_rds_instance` (PostgreSQL 16 with pgvector extension)
- `aws_elasticache_cluster` (Redis)
- `aws_s3_bucket` for PDFs + CloudFront distribution for frontend
- `aws_secretsmanager_secret` for all secrets (OpenAI key, DB password, etc.)
- `aws_alb` (Application Load Balancer) in front of ECS
- VPC with public/private subnets; ECS tasks in private subnet

Environment-specific configs via Terraform workspaces or `.tfvars` files.

Secrets flow: AWS Secrets Manager → ECS task `secrets` config → env vars in container (never in task definition JSON).

**Acceptance Criteria**
- [ ] `terraform apply` provisions all resources from scratch
- [ ] Public URL returns the frontend
- [ ] `POST /api/v1/documents` works end-to-end in production
- [ ] RDS has automated backups enabled
- [ ] All secrets in Secrets Manager, not in code or Terraform state

**Dependencies**
REGVIA-024, REGVIA-025

---

## Dependency Graph (Sequential Build Order)

```
✅ REGVIA-001 (monorepo)
  ├── ✅ REGVIA-002 (fe toolchain)
  │     └── ✅ REGVIA-003B (fe test infra)
  │           └── REGVIA-016 (fe scaffold) → REGVIA-017 (api client)
  │                                              ├── REGVIA-018 (upload UI)    [+ tests]
  │                                              ├── REGVIA-019 (chat UI)      [+ tests]
  │                                              └── REGVIA-020 (summary UI)   [+ tests]
  ├── ✅ REGVIA-003 (be toolchain)
  │     └── ✅ REGVIA-003A (be test infra)
  │           ├── REGVIA-014 (observability)
  │           ├── REGVIA-004 (ORM models + migration)
  │           │     └── REGVIA-004A (model factories + seed)
  │           │           ├── REGVIA-005 (storage client — MinIO local dev)
  │           │           │     └── REGVIA-006 (upload endpoint)    [+ tests]
  │           │           │           └── REGVIA-007 (processing)   [+ tests]
  │           │           │                 ├── REGVIA-008 (status endpoint)  [+ tests]
  │           │           │                 ├── REGVIA-009 (retrieval)        [+ tests]
  │           │           │                 │     └── REGVIA-010 (chat)       [+ tests]
  │           │           │                 │           ├── REGVIA-011 (streaming)
  │           │           │                 │           └── REGVIA-015 (langsmith)
  │           │           │                 └── REGVIA-012 (summary)          [+ tests]
  │           │           │                       └── REGVIA-015 (langsmith)
  │           │           └── (used as fixtures in integration tests)

E12 — Integration tests + coverage audit (after all features done):
  REGVIA-021 (be integration tests) ← REGVIA-003A, REGVIA-010, REGVIA-012
  REGVIA-022 (fe integration tests) ← REGVIA-003B, REGVIA-018, REGVIA-019, REGVIA-020
  REGVIA-023 (e2e)                  ← REGVIA-018, REGVIA-019, REGVIA-020

Deployment:
  REGVIA-024 (docker)    ← REGVIA-013
  REGVIA-025 (CI/CD)     ← REGVIA-021, REGVIA-022, REGVIA-023, REGVIA-024
  REGVIA-026A (S3/IAM)   ← REGVIA-005, REGVIA-025
  REGVIA-026 (AWS ECS)   ← REGVIA-026A, REGVIA-024, REGVIA-025
```

---

## Non-Negotiable Constraints

| # | Constraint |
|---|-----------|
| 1 | LLM must NEVER answer outside of retrieved document context |
| 2 | Every answer must include citations (chunk_id + page_number) |
| 3 | `found_in_document: false` must be returned — never a hallucinated answer |
| 4 | TanStack Query owns all server state — no useState for server data |
| 5 | Zustand owns UI state only — no server data in Zustand |
| 6 | All API responses validated with Zod on frontend / Pydantic on backend |
| 7 | Coverage thresholds enforced in CI — PRs cannot merge below 80% |
| 8 | No secrets in code, Dockerfiles, or Terraform state |
| 9 | LangSmith tracing enabled for all LLM calls |
| 10 | Atoms have zero business logic |
