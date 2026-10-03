# LLM-Based Interview Prep Platform

A comprehensive AI-powered interview preparation platform that generates personalized interview questions through a **provider-agnostic LLM layer** (Gemini, OpenAI, Anthropic, Groq, or local models), with full question management, full-text search, import/export, resume skill-gap analysis, mock interviews, and a statistics dashboard.

## Features

### AI & Question Intelligence

- **Provider-agnostic question generation** — every LLM call routes through a single LiteLLM-backed service; switch providers with the `LLM_MODEL` env var, no code changes
- **Fallback model chain** — a primary model plus configurable fallbacks (`LLM_FALLBACK_MODELS`) degrade gracefully during provider outages
- **Robust response parsing** — JSON-first parsing with a plain-text fallback, markdown-fence cleanup, and per-field validation/clamping
- **Job-title targeting** — questions customized for specific roles (Software Engineer, Data Scientist, etc.)
- **Question types** — technical, behavioral, and mixed questions with a 1–5 difficulty scale

### Question Management

- **Full CRUD** — create, read, update, and delete questions
- **Full-text search** — Postgres `tsvector`/`websearch_to_tsquery` with relevance ranking, and a case-insensitive `ILIKE` fallback on other dialects (SQLite in tests)
- **Filtering & pagination** — by job title, question type, flagged status; offset/limit pagination
- **Import / export** — bulk JSON import with per-entry validation (bad rows are skipped, not fatal) and streaming JSON/CSV export
- **Spreadsheet-injection protection** — CSV cells starting with `=`, `+`, `-`, `@`, tab, or CR are neutralized
- **Question sets** — group questions into named collections
- **Rating & flagging** — rate difficulty (1.0–5.0) and flag questions for review

### Documents & Skill Gap

- **Resume / JD upload** — multipart upload with skill, experience, and contact parsing
- **Skill-gap analysis** — compare a resume against a job description to surface matched, missing, and extra skills with a match percentage

### Mock Interviews

- **Interview sessions** — multi-turn mock interviews with configurable type and difficulty
- **Adaptive difficulty** — target difficulty adjusts based on evaluated performance
- **Transcripts & evaluations** — per-session message history and scored answer evaluations

### Analytics & Administration

- **Statistics dashboard** — totals, type/job-title breakdowns, difficulty distribution, plus dense time series (daily signups, daily evaluations, weekly score trend) that back the charts
- **Auth & roles** — register/login with Bearer session tokens, PBKDF2-HMAC-SHA256 password hashing, `user`/`admin` roles
- **Admin panel** — user listing/deletion, platform stats, global action history, flagged-question review

## Architecture

```
interview-helper/
├── backend/                 # FastAPI application
│   ├── main.py              # App factory, CORS, router wiring, lifespan
│   ├── database.py          # Engine, pooling, URL validation, get_db
│   ├── deps.py              # Auth dependencies (current/optional/admin user)
│   ├── models.py            # SQLAlchemy ORM models (source of truth)
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── routes/              # API route handlers
│   │   ├── questions.py     # Question CRUD, search, import/export, sets, rating
│   │   ├── stats.py         # Aggregated statistics + time series
│   │   ├── documents.py     # Document upload, skill-gap
│   │   ├── interviews.py    # Mock-interview sessions, messages, evaluations
│   │   ├── auth.py          # Register, login, logout, me, history
│   │   └── admin.py         # Admin-only user/question/history management
│   ├── services/            # Business logic
│   │   ├── llm_service.py   # Provider-agnostic LiteLLM client + fallback chain
│   │   ├── gemini_service.py# Question generation (routes through LLMService)
│   │   ├── interview_service.py
│   │   ├── evaluation_service.py
│   │   ├── document_service.py
│   │   ├── auth_service.py  # Password hashing, session tokens, roles
│   │   └── history_service.py
│   ├── alembic/             # Database migrations
│   ├── tests/               # pytest suite (522 tests)
│   └── Dockerfile           # Non-root, venv, gunicorn+uvicorn workers
├── frontend/                # React SPA (TypeScript + Vite)
│   ├── src/
│   │   ├── pages/           # Dashboard, Questions, Generate, Interview,
│   │   │                    # Stats, Documents, SkillGap, QuestionSets
│   │   ├── components/      # Reusable UI (cards, alerts, error boundary)
│   │   ├── services/api.ts  # Typed API client
│   │   └── types/index.ts   # Shared TypeScript types
│   ├── nginx.conf           # Production reverse proxy (serves /api to backend)
│   └── Dockerfile           # Multi-stage build, non-root nginx user
├── db/init.sql              # Legacy provisioning script (comments only; not mounted)
├── docker-compose.yml       # Development stack (hot reload)
├── docker-compose.dev.yml   # Bind-mount overrides for live reload
├── docker-compose.prod.yml  # Production stack (container-DB or RDS modes)
└── infra/                   # Terraform (EC2, RDS, ALB, security groups)
```

### Frontend

- **React 19 + TypeScript**, built with **Vite**
- **TanStack Query** for server state, **React Router** for routing
- **Tailwind CSS** for styling, **Recharts** for the dashboard charts
- Served in production by **nginx**, which proxies `/api` to the backend

### Backend

- **FastAPI** with automatic OpenAPI docs (`/docs`)
- **SQLAlchemy 2** ORM + **Alembic** migrations
- **LiteLLM** for provider-agnostic LLM calls
- **Gunicorn** with **Uvicorn** workers in production

### Database

- **PostgreSQL 15** in Docker/production; **SQLite** in the test suite
- Connection pooling (`QueuePool`, pre-ping, recycle) for server DBs; `NullPool` for SQLite
- Models in `backend/models.py` are the source of truth; Alembic owns the schema

## Quick Start (Docker)

### Prerequisites

- Docker and Docker Compose v2
- An LLM provider API key (e.g. Gemini) for question generation

### Run the stack

```bash
git clone <repository-url>
cd interview-helper

# Copy and configure the environment
cp .env.example .env   # or create .env manually
# Edit .env: set GEMINI_API_KEY (or another provider key + LLM_MODEL)

# Start the development stack
docker compose -f docker-compose.yml up --build
```

### Access

| Service            | URL                        |
| ------------------ | -------------------------- |
| Frontend           | http://localhost           |
| Backend API        | http://localhost:8000      |
| API docs (Swagger) | http://localhost:8000/docs |
| Database           | localhost:5432             |

### Development mode (live reload)

```bash
# Backend on :8000 with --reload, frontend Vite dev server on :5173 with HMR
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## Configuration

All configuration comes from environment variables (see `.env`). Nothing is hardcoded.

### Database

| Variable       | Default                                                 | Description                          |
| -------------- | ------------------------------------------------------- | ------------------------------------ |
| `DATABASE_URL` | `postgresql://postgres:postgres@db:5432/interview_prep` | SQLAlchemy connection URL (required) |
| `DB_NAME`      | `interview_prep`                                        | Postgres database name               |
| `DB_USER`      | `postgres`                                              | Postgres user                        |
| `DB_PASSWORD`  | (required in prod)                                      | Postgres password                    |
| `DB_PORT`      | `5432`                                                  | Host port for Postgres               |

### Application

| Variable            | Default                                     | Description                                 |
| ------------------- | ------------------------------------------- | ------------------------------------------- |
| `BACKEND_PORT`      | `8000`                                      | Host port for the backend                   |
| `FRONTEND_PORT`     | `80`                                        | Host port for the frontend (prod)           |
| `FRONTEND_DEV_PORT` | `5173`                                      | Host port for the Vite dev server           |
| `CORS_ORIGINS`      | `http://localhost:80,http://localhost:5173` | Comma-separated allowed origins             |
| `LOG_LEVEL`         | `INFO`                                      | Logging verbosity                           |
| `ENVIRONMENT`       | (unset)                                     | Set to `production` to enable strict checks |

> **CORS:** the backend enables credentials, so `CORS_ORIGINS` must be an explicit comma-separated list — a `*` wildcard is rejected at startup.

### LLM

| Variable              | Default                                                  | Description                    |
| --------------------- | -------------------------------------------------------- | ------------------------------ |
| `LLM_MODEL`           | `gemini/gemini-1.5-flash`                                | Primary model (LiteLLM name)   |
| `LLM_FALLBACK_MODELS` | `openai/gpt-4o-mini,anthropic/claude-3-5-haiku-20241022` | Comma-separated fallback chain |
| `LLM_TIMEOUT`         | `60`                                                     | Per-request timeout (seconds)  |
| `LLM_MAX_RETRIES`     | `2`                                                      | Provider retries               |
| `LLM_TEMPERATURE`     | `0.7`                                                    | Sampling temperature           |
| `GEMINI_API_KEY`      | —                                                        | Gemini provider key            |

Provider keys are read from the standard env vars (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `MISTRAL_API_KEY`, `COHERE_API_KEY`, `AZURE_API_KEY`, `VERTEX_AI_PROJECT_ID`, `AWS_ACCESS_KEY_ID`). Local providers (`ollama`) need no key.

### Auth

| Variable            | Default | Description            |
| ------------------- | ------- | ---------------------- |
| `SESSION_TTL_HOURS` | `24`    | Session token lifetime |

## API Endpoints

All routes are mounted under `/api`. Authentication uses `Authorization: Bearer <token>` where required; most read endpoints work anonymously.

### Questions — `/api/questions`

| Method | Path           | Auth     | Description                                  |
| ------ | -------------- | -------- | -------------------------------------------- |
| POST   | `/generate`    | optional | Generate questions with the LLM              |
| GET    | `/`            | public   | List/search/filter questions (paginated)     |
| GET    | `/export`      | public   | Export as JSON or CSV (`?format=json\|csv`)  |
| POST   | `/import`      | optional | Bulk-import questions (per-entry validation) |
| GET    | `/{id}`        | optional | Get one question                             |
| POST   | `/`            | optional | Create a question manually                   |
| PUT    | `/{id}`        | optional | Update a question                            |
| DELETE | `/{id}`        | optional | Delete a question                            |
| POST   | `/sets`        | public   | Create a question set                        |
| GET    | `/sets/`       | public   | List question sets                           |
| POST   | `/rate`        | optional | Rate a question (1.0–5.0)                    |
| GET    | `/job-titles/` | public   | List distinct job titles                     |

**Query params (list & export):** `skip`, `limit` (1–1000), `q` (free-text search, max 200 chars), `job_title`, `question_type` (`technical`/`behavioral`/`mixed`), `flagged_only`.

### Statistics — `/api/stats`

| Method | Path | Auth   | Description                                                                                    |
| ------ | ---- | ------ | ---------------------------------------------------------------------------------------------- |
| GET    | `/`  | public | Aggregated stats + 7-day signup/evaluation series, difficulty distribution, 8-week score trend |

### Documents — `/api/documents`

| Method | Path         | Auth | Description                                 |
| ------ | ------------ | ---- | ------------------------------------------- |
| POST   | `/upload`    | user | Upload a resume/JD (`?document_type=`)      |
| GET    | `/`          | user | List uploaded documents                     |
| DELETE | `/{id}`      | user | Delete a document                           |
| POST   | `/skill-gap` | user | Compare resume vs JD (`?resume_id=&jd_id=`) |

### Interviews — `/api/interviews`

| Method | Path                         | Auth | Description                |
| ------ | ---------------------------- | ---- | -------------------------- |
| POST   | `/sessions`                  | user | Start an interview session |
| GET    | `/sessions`                  | user | List sessions              |
| GET    | `/sessions/{id}`             | user | Get a session              |
| GET    | `/sessions/{id}/messages`    | user | Get the transcript         |
| GET    | `/sessions/{id}/evaluations` | user | Get answer evaluations     |
| POST   | `/sessions/{id}/answer`      | user | Submit an answer           |
| POST   | `/model-answer`              | user | Get a model answer         |

### Auth — `/api/auth`

| Method | Path        | Auth   | Description                         |
| ------ | ----------- | ------ | ----------------------------------- |
| POST   | `/register` | public | Register (first user becomes admin) |
| POST   | `/login`    | public | Login, returns a session token      |
| POST   | `/logout`   | user   | Invalidate the session              |
| GET    | `/me`       | user   | Current user profile                |
| GET    | `/history`  | user   | Action history                      |

### Admin — `/api/admin` (requires `admin` role)

| Method | Path                 | Description                  |
| ------ | -------------------- | ---------------------------- |
| GET    | `/users`             | List users                   |
| DELETE | `/users/{id}`        | Delete a user                |
| GET    | `/stats`             | Platform-wide statistics     |
| GET    | `/history`           | Global action history        |
| GET    | `/questions/flagged` | Flagged questions for review |
| DELETE | `/questions/{id}`    | Delete any question          |

### System

| Method | Path      | Description                |
| ------ | --------- | -------------------------- |
| GET    | `/`       | API info                   |
| GET    | `/health` | Liveness + DB connectivity |

## LLM Integration

The platform is **provider-agnostic**. `services/llm_service.py` wraps `litellm.completion` with a fallback chain:

1. Try the primary `LLM_MODEL`.
2. On failure or an empty response, walk `LLM_FALLBACK_MODELS`.
3. If every provider fails, raise `LLMServiceError` (the `/generate` endpoint returns `503`).

Question generation (`services/gemini_service.py`) builds a structured prompt, asks for a JSON array, and parses the response with a JSON-first / text-fallback strategy. Difficulty is clamped to 1–5 and question type is validated, so malformed model output never corrupts the database.

To use a different provider, set `LLM_MODEL` and the matching key, e.g.:

```bash
LLM_MODEL=openai/gpt-4o-mini OPENAI_API_KEY=sk-...
# or
LLM_MODEL=anthropic/claude-3-5-haiku-20241022 ANTHROPIC_API_KEY=sk-ant-...
# or a local model
LLM_MODEL=ollama/llama3
```

## Database Migrations (Alembic)

Schema changes are managed with **Alembic** (`backend/alembic/`). The SQLAlchemy models are the source of truth.

```bash
cd backend

# Create a migration from model changes
alembic revision --autogenerate -m "describe the change"

# Review alembic/versions/, then apply
alembic upgrade head

# Check status
alembic current
```

`Base.metadata.create_all()` still runs on startup as a **development fallback** (it logs that it is a fallback), so a fresh local database works without running migrations manually. In production, always use migrations.

### Fresh database (Docker)

```bash
# Start an empty database
docker compose -f docker-compose.yml up -d db

# Apply all migrations (creates every table)
docker compose -f docker-compose.yml run --rm backend /app/venv/bin/alembic upgrade head

# Then start the rest of the stack
docker compose -f docker-compose.yml up -d
```

> **Note:** `db/init.sql` is no longer mounted into the Postgres image. Fresh volumes start empty so Alembic owns the schema. For an existing database created with `create_all()` (no `alembic_version` table), run `alembic stamp head` once to bring it under migration management.

## Development

### Prerequisites

- Docker and Docker Compose (for the full stack)
- Node.js 20+ and Python 3.11+ (for local development)

### Local backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload          # http://localhost:8000
```

### Local frontend

```bash
cd frontend
npm install
npm run dev                        # Vite dev server on http://localhost:5173
```

### Linting & formatting

- **Python:** `ruff check .` and `ruff format .` (pinned to ruff 0.6.9 in pre-commit)
- **Frontend:** `npm run lint` (ESLint) and `npm run format` (Prettier)
- **Pre-commit:** `pre-commit install` then `pre-commit run --all-files` — runs ruff, ruff-format, prettier, trailing-whitespace, end-of-file-fixer, check-yaml, check-json, check-merge-conflict, and check-added-large-files

## Testing

```bash
cd backend
pytest                              # run the suite
pytest --cov=. --cov-report=term    # with coverage
```

- **522 tests** across API, services, models, schemas, auth, RBAC, and lifecycle
- **Coverage gate: 90%** (enforced by `.coveragerc` `fail_under` and `scripts/check_coverage.sh`); the suite currently sits at **~96%**
- Tests run against in-memory SQLite; Postgres-specific SQL (full-text search, date bucketing) is dialect-detected so the same code serves both

## Security

- **No secrets in the repo** — all credentials come from environment variables; `.env` and `terraform.tfvars` are gitignored and never tracked
- **Non-root containers** — backend runs as `appuser`, frontend as `nginxuser`
- **Password hashing** — PBKDF2-HMAC-SHA256 with a per-user salt and 200k iterations
- **Session tokens** — `secrets.token_urlsafe(32)`, stored as SHA-256 hashes
- **SQL injection** — all queries use bound parameters; `LIKE` wildcards are escaped; search terms are parameterized
- **CSV injection** — exported cells are neutralized
- **Input validation** — Pydantic schemas validate every request; difficulty, ratings, and counts are range-checked
- **CORS** — credentials are enabled, so origins must be an explicit list (a `*` wildcard is rejected at startup)
- **Production guards** — `ENVIRONMENT=production` rejects default credentials in `DATABASE_URL`; prod compose requires `DB_PASSWORD`
- **Dependency pinning** — backend `requirements.txt` is fully pinned (`==`); frontend uses a lockfile

## Deployment

### Production (Docker Compose)

```bash
# Containerized database mode (set DB_NAME/DB_USER/DB_PASSWORD in .env)
docker compose -f docker-compose.prod.yml --profile container-db up -d

# RDS mode (set DATABASE_URL to the RDS endpoint in .env)
docker compose -f docker-compose.prod.yml up -d
```

The prod stack adds `restart: unless-stopped`, memory/CPU limits, and a profile-gated database service so one file supports both container-DB and RDS modes.

### Infrastructure (Terraform)

The `infra/` directory provisions AWS infrastructure: EC2 (with SSM-based administration, SSH opt-in), RDS PostgreSQL in private subnets with encryption and automated backups, an ALB, and security groups that only expose 80/443. Secrets are passed via `TF_VAR_*` environment variables or a git-ignored `terraform.tfvars`; see `infra/terraform.tfvars.example`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [plans/](plans/) directory for the improvement roadmap.

## License

See the repository license file.
