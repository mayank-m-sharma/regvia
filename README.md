# RegVia — Compliance Copilot

An AI-powered document analysis platform that helps compliance teams extract, understand, and act on regulatory documents. Upload PDFs, ask natural language questions, get cited answers, and generate structured compliance summaries.

---

## What it does

- **Document Chat** — Ask questions about uploaded regulatory PDFs; get AI answers with direct page citations
- **Knowledge Library** — Build a library of documents and run cross-document RAG queries
- **Compliance Summary** — Auto-generate structured summaries (obligations, risks, gaps, recommendations)
- **Persistent Sessions** — Chat history with auto-generated titles, resumable conversations
- **Real-time Streaming** — Token-level streaming via Server-Sent Events

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript, Vite, Tailwind CSS, Zustand, React Query |
| Backend | FastAPI (async), Python 3.12, SQLAlchemy 2.0, Alembic |
| Database | PostgreSQL 16 + pgvector (vector similarity search) |
| Task Queue | Celery + Redis (with Flower monitoring UI) |
| Storage | AWS S3 (production) / MinIO (local dev) |
| AI | OpenAI GPT-4o-mini + embeddings (production), Ollama (local fallback) |
| Observability | OpenTelemetry → Jaeger, Loguru (JSON), LangSmith (LLM tracing) |
| Auth | Google OAuth2 + JWT |
| Infrastructure | AWS EC2 + CloudFront CDN, Docker Compose, Nginx |

---

## Quick Start (Local)

### Prerequisites
- Docker & Docker Compose
- Google OAuth2 credentials (for login)
- OpenAI API key (optional — Ollama works locally)

### 1. Clone and configure

```bash
git clone <repo-url>
cd regVia
```

Create `backend/.env.local` from the example:

```bash
cp backend/.env.local.example backend/.env.local
```

Fill in at minimum:

```env
GOOGLE_CLIENT_ID=<your-client-id>
GOOGLE_CLIENT_SECRET=<your-client-secret>
OPENAI_API_KEY=<your-openai-key>         # or leave blank to use Ollama
JWT_SECRET_KEY=<any-32-char-secret>
```

### 2. Start all services

```bash
docker compose up -d
```

### 3. Access

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000/api/v1 |
| API Docs (Swagger) | http://localhost:8000/api/v1/docs |
| MinIO Console | http://localhost:9001 |
| Celery Flower | http://localhost:5555 |
| Jaeger UI | http://localhost:16686 |

---

## Manual Development Setup (without Docker)

### Backend

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# Optional: Celery worker (if USE_CELERY=true)
uv run celery -A app.worker.celery_app worker --loglevel=info
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

---

## Project Structure

```
regVia/
├── backend/
│   ├── app/
│   │   ├── api/v1/           # Route handlers (auth, documents, chat)
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic (RAG, embedding, summary, processing)
│   │   ├── worker/           # Celery tasks
│   │   ├── core/             # Settings, auth, telemetry
│   │   ├── middleware/       # Request logging
│   │   └── storage/          # S3 client abstraction
│   ├── alembic/              # Database migrations
│   └── tests/                # pytest unit + integration tests
├── frontend/
│   └── src/
│       ├── components/       # Atomic Design (atoms → molecules → organisms → pages)
│       ├── features/         # Feature-specific hooks and logic
│       ├── shared/           # API client, types, utilities
│       └── store/            # Zustand global state
├── nginx/                    # Nginx reverse proxy config (production)
├── docker-compose.yml        # Local dev services
├── docker-compose.prod.yml   # Production overrides
├── DEPLOY.md                 # AWS deployment guide
└── ARCHITECTURE.md           # System design and architecture details
```

---

## API Overview

**Base URL:** `/api/v1`

| Method | Path | Description |
|---|---|---|
| GET | `/auth/login` | Get Google OAuth2 URL |
| POST | `/auth/exchange` | Exchange OAuth code for JWT |
| GET | `/auth/me` | Get current user |
| GET | `/documents` | List user's documents |
| POST | `/documents` | Upload a PDF |
| DELETE | `/documents/{id}` | Delete a document |
| POST | `/documents/{id}/summary` | Generate compliance summary |
| GET | `/chat/sessions` | List chat sessions |
| POST | `/chat/sessions` | Create a session |
| GET | `/chat/sessions/{id}` | Get session with messages |
| POST | `/chat` | Send a message (non-streaming) |
| POST | `/chat/stream` | Send a message (SSE streaming) |

---

## Environment Variables

### Backend (key variables)

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://regvia:regvia@localhost:5432/regvia` |
| `OPENAI_API_KEY` | OpenAI key (required in production) | — |
| `GOOGLE_CLIENT_ID` | OAuth2 client ID | — |
| `GOOGLE_CLIENT_SECRET` | OAuth2 client secret | — |
| `GOOGLE_REDIRECT_URI` | OAuth2 callback URL | `http://localhost:5173/auth/callback` |
| `JWT_SECRET_KEY` | JWT signing secret (min 32 chars) | — |
| `S3_BUCKET_NAME` | S3 bucket for documents | `regvia-documents` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `AWS_ACCESS_KEY_ID` | AWS credentials | — |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials | — |
| `S3_ENDPOINT_URL` | Override S3 endpoint (MinIO for local) | — |
| `USE_CELERY` | Use Celery for background tasks | `false` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `OTEL_ENABLED` | Enable OpenTelemetry tracing | `false` |
| `LANGCHAIN_API_KEY` | LangSmith tracing | — |
| `APP_ENV` | `local` or `production` | `local` |

---

## Running Tests

### Backend

```bash
cd backend
uv run pytest
```

### Frontend

```bash
cd frontend
pnpm test
```

---

## Deployment

See [DEPLOY.md](DEPLOY.md) for the complete step-by-step AWS deployment guide (CloudFront + EC2 + Nginx, no domain name required).

Production architecture: `Browser → CloudFront (HTTPS) → EC2 Nginx → FastAPI / React / Flower / Jaeger`
