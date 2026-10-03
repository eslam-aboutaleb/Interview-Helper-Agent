# Competitive Analysis & Recommendations

> Review of the Interview-Helper-Agent against public interview-prep repos on GitHub,
> with a prioritized roadmap to make it superior.

## Competitive landscape (repos reviewed)

| Repo                             | Stack                                     | Standout features                                                                           |
| -------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------- |
| PrepLabsAI/InterviewMentor (91★) | Claude skills                             | Role-specific interviewers, 4-level hint system, adaptive difficulty, progress tracking     |
| Edge-Explorer/Interview-Prep     | FastAPI + Gemini + React/Vite             | 383-company intelligence, agentic discovery loop (LangGraph), Alembic, voice, panel mode    |
| TurjoyBari/ai-mock-interview     | Next.js + Prisma + Gemini                 | ATS resume scoring, JD match, voice STT/TTS, Monaco code editor, Recharts                   |
| Mohdtalibakhtar/PrepareMe        | FastAPI + Pydantic-AI + Groq              | Adaptive assessment loop, mock interview streaming, daily practice cron, cold-email suite   |
| BhupatiNadar/ai-interview-coach  | Streamlit + LangChain + Supabase          | Resume parsing, STAR evaluation, 4-week AI learning plan, voice mode                        |
| AnupDangi/SmartAIInterviewer     | Google ADK + Gemini                       | Multi-agent (coordinator + coding agent), live code execution (Piston), session persistence |
| trishthakur/Mock-Interview-Agent | Streamlit + FAISS + Sentence-Transformers | RAG-grounded question generation, Chain-of-Thought evaluation                               |
| Rajbharti06/IntervAI             | FastAPI + React/Vite                      | Silence detection, adaptive personality, streaming TTS, anti-cheat, gamification            |
| pplam/prepme (22★)               | Static HTML skill                         | JD + CV → predicted questions with follow-up chains, offline study sheet                    |

## Gap analysis: what competitors have that this app lacks

| Capability                                      | Competitors | This app (before)        | Priority |
| ----------------------------------------------- | ----------- | ------------------------ | -------- |
| Resume / JD ingestion & parsing                 | ~all        | ❌ none                  | **P0**   |
| Mock interview session (multi-turn, follow-ups) | ~all        | ❌ static questions only | **P0**   |
| Answer evaluation & scoring (STAR / rubric)     | ~all        | ❌ none                  | **P0**   |
| Model answers for comparison                    | most        | ❌ none                  | **P0**   |
| Adaptive difficulty                             | most        | ❌ static 1-5            | **P0**   |
| Skill-gap analysis (resume vs JD)               | most        | ❌ none                  | P1       |
| Company-specific question mode                  | several     | ❌ none                  | P1       |
| Learning plan / study roadmap                   | several     | ❌ none                  | P1       |
| Charts / radar dashboards                       | several     | ❌ basic stats only      | P1       |
| Voice mode (STT/TTS)                            | several     | ❌ none                  | P2       |
| RAG-grounded generation                         | few         | ❌ none                  | P2       |
| Code execution sandbox                          | few         | ❌ none                  | P2       |
| Gamification (XP, streaks)                      | few         | ❌ none                  | P2       |
| OAuth (Google/GitHub)                           | several     | ❌ email/pass only       | P2       |

## What makes this app superior: the differentiators to build

1. **Full interview loop, not just a question bank.** Resume/JD ingestion → skill-gap analysis → adaptive mock interview → per-answer evaluation → model answers → weakness-driven study plan. Most competitors stop at one of these stages.
2. **Multi-agent orchestration** (coordinator / interviewer / evaluator / coach) with a deterministic state machine — the pattern used by the strongest repos (SmartAIInterviewer, PrepareMe, MockMate).
3. **Grounded generation** via RAG over a curated question bank so questions cite real role/JD context instead of model priors.
4. **Production-grade platform**: Terraform IaC, Alembic migrations, pre-commit (ruff + prettier), tests, CI/CD, observability — most competitors are demo-grade.
5. **Modern frontend**: Vite + React Query + shadcn/ui with charts, replacing the deprecated CRA setup.

## Review of current features — how to make them better

### Question generation (current: single-shot Gemini prompt)

- **Better**: structured output via the new `google-genai` SDK (the current `google.generativeai` package is end-of-life), role/seniority/company-aware prompts, follow-up question chains, and model answers. Add a curated question bank + RAG for grounding.

### Question management (current: CRUD + sets + ratings)

- **Better**: full-text search (Postgres `tsvector`), tag hierarchy, versioning/audit log, shareable sets, import/export (JSON/CSV/Anki), and a community rating system.

### Statistics (current: counts + averages)

- **Better**: per-category radar charts, difficulty distribution, progress-over-time series, weakness heatmap, and session-based scoring trends (Recharts).

### User tracking (added this session: users, sessions, question_history)

- **Better**: persist mock-interview sessions and per-answer evaluations, compute skill-gap vectors, and drive adaptive difficulty from real performance data.

### Auth (added this session: register/login/sessions)

- **Better**: OAuth (Google/GitHub), refresh-token rotation, password reset, email verification, and role-based access.

### Deployment (current: 856-line interactive shell script)

- **Better**: Terraform modules for VPC/EC2/RDS/IAM/security-groups, GitHub Actions CI/CD, and secrets in AWS Secrets Manager. (Implemented in `infra/`.)

### Frontend (current: CRA + hardcoded EC2 URL)

- **Better**: Vite, React Query caching, shadcn/ui design system, skeleton loaders, optimistic updates, and a mock-interview chat UI. (Implemented in `frontend/`.)

## Prioritized implementation roadmap

**P0 — core interview loop (implemented this session)**

- Resume/JD parsing service + endpoints (`services/document_service.py`)
- Mock-interview session engine with adaptive difficulty (`services/interview_service.py`)
- Answer evaluation with rubric + STAR scoring (`services/evaluation_service.py`)
- Model-answer generation
- Session + evaluation persistence (new DB tables)

**P1 — intelligence**

- Skill-gap analysis (resume vs JD)
- Company-specific question mode
- AI learning-plan generation
- Charts dashboard

**P2 — polish**

- Voice mode (Whisper STT + TTS)
- RAG grounding (FAISS)
- Code execution sandbox (Piston/Judge0)
- Gamification, OAuth, leaderboards

## AI framework decision: no heavy framework

**Decision: do NOT adopt LangChain/LangGraph/ADK.** The app's AI needs are
linear pipelines (prompt → parse → score → adapt), not multi-agent graphs.
A heavy framework would add dependency bloat, abstraction leaks, and version
churn without buying anything the current architecture lacks. What the app
actually needs, and now has:

| Need                    | Solution                                           | Status         |
| ----------------------- | -------------------------------------------------- | -------------- |
| Provider abstraction    | **LiteLLM** (`services/llm_service.py`)            | ✅ Implemented |
| Structured output       | Pydantic + tolerant JSON parsing                   | ✅ Implemented |
| Interview orchestration | Hand-rolled state machine (`interview_service.py`) | ✅ Implemented |
| Fallback/degradation    | Model fallback chain + heuristic scoring           | ✅ Implemented |

Revisit LangGraph only if genuinely multi-agent workflows emerge (e.g. a
dedicated "interviewer" agent plus a "resume reviewer" agent negotiating).

### LiteLLM as the LLM abstraction layer

All LLM calls route through `LLMService` (backed by LiteLLM), so the
provider is a configuration choice, not a code change:

- `LLM_MODEL` — primary model, e.g. `gemini/gemini-1.5-flash`,
  `openai/gpt-4o-mini`, `anthropic/claude-3-5-haiku-20241022`,
  `groq/llama-3.1-8b-instant`, `ollama/llama3` (local, no key needed)
- `LLM_FALLBACK_MODELS` — comma-separated chain tried on failure
- `LLM_TIMEOUT`, `LLM_MAX_RETRIES`, `LLM_TEMPERATURE`
- API keys are resolved per provider (`GEMINI_API_KEY`, `OPENAI_API_KEY`,
  `ANTHROPIC_API_KEY`, …); unconfigured providers are skipped automatically

`google-generativeai` was removed from requirements — LiteLLM speaks the
Gemini API directly, and the EOL SDK is no longer needed anywhere.

## Authorization: roles and responsibilities

RBAC with two roles (`user`, `admin`), enforced by the
`get_current_admin_user` dependency (403 for non-admins). The **first
registered user is bootstrapped as admin** so a fresh deployment always has
exactly one admin with no manual setup.

### Regular user capabilities

- Register / login / logout (session tokens, PBKDF2-hashed passwords)
- Generate AI interview questions; browse, search, and filter the bank
- Create, edit, and rate questions; view their own interaction history
- Upload resume / job-description documents (PDF/DOCX/TXT)
- Run resume-vs-JD skill-gap analysis
- Run multi-turn mock interviews with adaptive difficulty and AI scoring
- Request model answers for practice questions

### Admin capabilities (everything a user can do, plus)

- **User management**: list users, promote/demote roles, deactivate,
  delete accounts (self-demotion/self-deletion blocked)
- **Platform dashboard**: user/question/session/evaluation counts,
  average scores, 7-day signups (`GET /api/admin/stats`)
- **Question moderation**: review flagged questions, delete any question
- **Audit log**: platform-wide action history with user/action filters
  (`GET /api/admin/history`)

## Recommended AI frameworks (future, optional)

| Need           | Recommendation                         | Why                                                    |
| -------------- | -------------------------------------- | ------------------------------------------------------ |
| Embeddings/RAG | Sentence-Transformers + FAISS/pgvector | Grounded question generation from a curated bank (P2). |
| Voice          | Whisper (STT) + Gemini/OpenAI TTS      | Realistic spoken interviews (P2).                      |
| Code execution | Piston or Judge0 (sandboxed)           | Safe coding-interview verification (P2).               |
| Scheduling     | APScheduler                            | Daily practice questions, session cleanup (P2).        |
