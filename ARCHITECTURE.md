# RegVia — System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Browser (User)                               │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ HTTPS
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    AWS CloudFront CDN                               │
│              (free TLS cert, *.cloudfront.net domain)              │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ HTTP
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     EC2 t3.large (Amazon Linux 2023)               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      Nginx (port 80)                        │   │
│  │  /           → React SPA (static files)                     │   │
│  │  /api/       → FastAPI backend (port 8000)                  │   │
│  │  /flower/    → Celery Flower UI (port 5555)                 │   │
│  │  /jaeger/    → Jaeger tracing UI (port 16686)               │   │
│  └──────────┬──────────────────────────────────────────────────┘   │
│             │ Docker network (regvia_default)                       │
│  ┌──────────▼──────────────────────────────────────────────────┐   │
│  │  FastAPI Backend          │  Celery Worker                  │   │
│  │  - REST API               │  - process_document_task        │   │
│  │  - SSE streaming          │  - 3× retry with backoff        │   │
│  │  - JWT auth               │                                 │   │
│  └──────────┬────────────────┴────────┬────────────────────────┘   │
│             │                         │                             │
│  ┌──────────▼──────────┐  ┌──────────▼──────────┐                 │
│  │  PostgreSQL + pgvec │  │       Redis          │                 │
│  │  - Users            │  │  - Celery broker     │                 │
│  │  - Documents        │  │  - Task results      │                 │
│  │  - Chunks           │  └─────────────────────┘                 │
│  │  - Embeddings       │                                           │
│  │  - Chat sessions    │  ┌─────────────────────┐                 │
│  │  - Messages         │  │       Jaeger         │                 │
│  │  - Summaries        │  │  - Distributed trace │                 │
│  └─────────────────────┘  │  - OTLP HTTP ingest  │                 │
│                            └─────────────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            │ AWS SDK (boto3)
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     AWS S3 Bucket                                   │
│              (PDF document storage, IAM-scoped access)             │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            │ HTTPS API
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  OpenAI API                                         │
│  - text-embedding-3-small (1536 dims) — document embeddings        │
│  - gpt-4o-mini — chat completions, summaries, session titles       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Document Processing Pipeline

```
User uploads PDF
      │
      ▼
POST /api/v1/documents
      │
      ├─ Validate (content-type, size ≤ 50MB)
      ├─ SHA-256 hash → check for duplicate
      ├─ Upload to S3 (documents/{uuid}/{filename})
      ├─ Create Document row (status=pending)
      └─ Enqueue task
            │
            ├─ USE_CELERY=true  → Celery task (Redis broker)
            └─ USE_CELERY=false → FastAPI BackgroundTask
                  │
                  ▼
         process_document(document_id)
                  │
                  ├─ 1. Extract text (pdfplumber) — page by page
                  ├─ 2. Chunk (tiktoken)
                  │      512 tokens / chunk
                  │      50-token overlap
                  │      min 100 tokens (drop small tail chunks)
                  ├─ 3. Embed (OpenAI text-embedding-3-small)
                  │      Batched in groups of 100
                  ├─ 4. Store Chunk + Embedding rows in PostgreSQL
                  └─ 5. Update Document.status = ready
                         (or failed on error → retry up to 3×)
```

---

## RAG Query Flow (Chat)

```
User sends question
      │
      ▼
POST /api/v1/chat/stream
      │
      ├─ Authenticate (JWT)
      ├─ Get or create ChatSession
      ├─ Embed question (same model as documents)
      │
      ├─ Document mode (document_id set):
      │      pgvector cosine similarity on document's chunks
      │      top-5 chunks returned
      │
      └─ Library mode (document_id=null):
             pgvector cosine similarity across all user's ready docs
             top-10 chunks returned
                  │
                  ▼
         Build prompt:
         [System: answer only from context, cite chunks]
         [Context: chunk 1... chunk 2... chunk N]
         [History: prior turns]
         [Human: question]
                  │
                  ▼
         OpenAI streaming (gpt-4o-mini)
                  │
                  ├─ Token chunks → SSE events → browser
                  ├─ Extract [chunk:uuid] citations from full answer
                  └─ Save Message row + update session metadata
```

---

## Authentication Flow

```
1. User clicks "Sign in with Google"
   GET /api/v1/auth/login
   ← { url: "https://accounts.google.com/o/oauth2/auth?...", state: "random" }

2. Browser redirects to Google
   Google asks user to sign in and consent

3. Google redirects back to /auth/callback?code=XXX&state=YYY

4. Frontend validates state (CSRF protection), calls:
   POST /api/v1/auth/exchange { code: "XXX" }
   Backend exchanges code with Google → gets user profile
   Creates/updates User row in DB
   ← { token: "eyJ..." } (JWT, 7-day expiry)

5. All subsequent requests include:
   Authorization: Bearer eyJ...
```

---

## Database Schema

```
users
├── id (UUID PK)
├── email (unique)
├── display_name
├── avatar_url
├── created_at
└── last_login_at

documents
├── id (UUID PK)
├── owner_id (FK → users)
├── filename
├── s3_key
├── size_bytes
├── content_hash (SHA-256, for dedup)
├── status (pending | processing | ready | failed)
├── chunk_count
├── in_library (bool — Knowledge Library membership)
├── created_at
└── updated_at

chunks
├── id (UUID PK)
├── document_id (FK → documents)
├── content (text)
├── page_number
├── chunk_index
└── token_count

embeddings
├── id (UUID PK)
├── chunk_id (FK → chunks, unique)
└── vector (vector(1536)) ← pgvector column

chat_sessions
├── id (UUID PK)
├── user_id (FK → users)
├── document_id (FK → documents, nullable — null = library mode)
├── title
├── created_at
└── last_message_at

messages
├── id (UUID PK)
├── session_id (FK → chat_sessions)
├── role (user | assistant)
├── content
├── citations (JSONB — [{ chunk_id, page_number, excerpt }])
└── created_at

summaries
├── id (UUID PK)
├── document_id (FK → documents, unique)
├── obligations (JSONB)
├── risks (JSONB)
├── gaps (JSONB)
├── recommendations (JSONB)
└── created_at
```

---

## Compliance Summary Generation

```
POST /documents/{id}/summary
      │
      ├─ Check cache (summaries table) → return if exists
      │
      ├─ Load all chunks for document
      │
      ├─ Strategy selection:
      │      chunks ≤ 30 → DIRECT strategy
      │      chunks > 30 → MAP-REDUCE strategy
      │
      ├─ DIRECT:
      │      Single LLM call with all chunks as context
      │      Force JSON output with structured schema
      │
      └─ MAP-REDUCE:
             Split chunks into batches of ~15
             For each batch → mini-summary (obligations/risks/gaps/recs)
             Aggregate all mini-summaries
             Final LLM call → synthesize into single structured summary
                  │
                  ▼
         Store in summaries table
         Return { obligations, risks, gaps, recommendations }
         Each item: { text, severity/priority, page_number?, chunk_id? }
```

---

## Observability Stack

```
Request arrives
      │
      ▼
Request Logging Middleware
├── Inject request_id (UUID) into log context
├── Log: method, path, status, duration_ms
└── Propagate request_id to all log statements

      │ (parallel)
      ▼
OpenTelemetry Auto-Instrumentation
├── FastAPI → spans for every route handler
├── SQLAlchemy → spans for every DB query
└── httpx → spans for outbound HTTP (OpenAI calls)
      │
      ▼
OTLP HTTP Exporter → Jaeger (port 4318)
      │
      ▼
Jaeger UI (/jaeger/) — visualize traces, latency, errors

LangSmith Tracing (LLM calls only)
├── @traceable on: _call_llm, _call_llm_stream, generate_summary
├── Captures: prompt, completion, token counts, latency
└── LangSmith UI — evaluate, debug, compare LLM runs

Celery Flower (/flower/) — task queue monitoring
├── Active tasks
├── Worker status
├── Task history and failure rates
└── Retry counts
```

---

## Key Architectural Decisions

### Why pgvector instead of a dedicated vector DB?
Keeps the stack simple — one PostgreSQL instance serves both relational and vector data. For the current scale (thousands of documents per user), pgvector with an HNSW or IVFFlat index is more than sufficient. Avoids operational overhead of a separate Pinecone/Weaviate/Qdrant service.

### Why Celery instead of FastAPI BackgroundTasks?
BackgroundTasks run in-process and are lost if the server crashes mid-processing. Celery persists tasks in Redis, provides retry guarantees, and allows horizontal scaling of workers independently of the API. The `USE_CELERY` flag lets you use BackgroundTasks locally (simpler) and Celery in production (durable).

### Why SSE instead of WebSockets for streaming?
SSE is unidirectional (server → client), which is exactly what token streaming needs. It works over standard HTTP/1.1, is trivially proxied through Nginx and CloudFront, and doesn't require a persistent connection upgrade. WebSockets add complexity with no benefit for this use case.

### Why CloudFront instead of buying a domain?
For a short-lived deployment, CloudFront provides free HTTPS via `*.cloudfront.net` with no domain purchase or DNS configuration required. It also handles global CDN caching for static assets and acts as a secure reverse proxy to the EC2 instance.

### Why Docker Compose instead of Kubernetes?
Right-sized for a single EC2 instance. Kubernetes adds significant operational overhead (control plane, node management, networking) that isn't justified at this scale. Docker Compose gives all the benefits of containerization (reproducible environments, service isolation, easy restarts) without the complexity.

### Embedding Provider Abstraction
A protocol-based duck-typing approach allows swapping OpenAI ↔ Ollama at runtime via environment variables. In production, `OPENAI_API_KEY` being set triggers OpenAI. Locally, without the key, it falls back to Ollama running on `localhost:11434`. The same `EmbeddingProvider` interface means the RAG service is provider-agnostic.

---

## Local vs Production Differences

| Concern | Local Dev | Production |
|---|---|---|
| Object Storage | MinIO (Docker, port 9000) | AWS S3 |
| Task Queue | FastAPI BackgroundTasks | Celery + Redis |
| Frontend | Vite dev server (HMR) | Pre-built static files via Nginx |
| HTTPS | HTTP only (localhost) | CloudFront TLS |
| Logging | Human-readable (colored) | Structured JSON |
| Tracing | Disabled by default | OpenTelemetry → Jaeger |
| AI Model | Ollama (local) or OpenAI | OpenAI only |
| Auth callback | `http://localhost:5173/auth/callback` | `https://<cf-domain>/auth/callback` |

---

## Security Considerations

- **JWT tokens** expire after 7 days; no refresh token mechanism (re-login required)
- **Row-level security** enforced in application layer — every DB query filters by `owner_id = current_user.id`
- **S3 access** uses a dedicated IAM user (`regvia-prod-app`) with minimal permissions (only `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket` on the app bucket)
- **CORS** restricted to known origins (localhost in dev, CloudFront domain in production)
- **OAuth2 state parameter** stored in `sessionStorage` and validated before code exchange (CSRF protection)
- **EC2 Security Group** allows SSH only from creator's IP, HTTP only from CloudFront (port 80)
- **Secrets** never committed — all sensitive values in `.env.local` / `.env.prod` (gitignored)
