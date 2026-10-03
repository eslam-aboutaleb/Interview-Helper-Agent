# Plan 10 — P2 backlog (unscheduled)

- **Wave:** 3 — documentation only; **do not execute** in this cycle
- **Depends on:** all wave-2 plans
- **Priority:** P2 — captured from RECOMMENDATIONS.md for future planning

## Objective

Record the remaining P2 enhancements with enough detail (approach, deps,
rough tasks) that a future cycle can pick them up without re-doing the
analysis. No code in this plan.

## Items

### 10.1 Voice mode (Whisper STT + TTS)
- **Value:** spoken mock interviews.
- **Approach:** browser `MediaRecorder` → upload audio to
  `POST /api/interviews/sessions/{id}/answer` (add `audio` part); backend
  transcribes with OpenAI Whisper via LiteLLM (`whisper-1`) or an
  open-source Whisper container; TTS via Gemini/OpenAI for interviewer voice.
- **Deps:** `openai-whisper` or LiteLLM audio support; storage for audio
  blobs (S3 or DB bytea); nginx `client_max_body_size` increase.
- **Risks:** latency, cost, PII in audio — add an explicit consent flag.

### 10.2 RAG-grounded question generation
- **Value:** questions cite real role/JD context instead of model priors.
- **Approach:** embed a curated question bank with `pgvector` (Postgres
  extension) or FAISS; retrieve top-k similar questions as few-shot context
  for generation; cite sources in the response.
- **Deps:** `pgvector` extension on RDS (check `infra/rds.tf` — needs
  `engine = "postgres"` with vector extension enabled) or FAISS +
  sentence-transformers.
- **Risks:** embedding model choice; index rebuild cost.

### 10.3 Code execution sandbox
- **Value:** verify coding-interview answers.
- **Approach:** call Piston (self-hosted container) or Judge0 API from a new
  `POST /api/interviews/run-code` endpoint; stream stdout/stderr/exit code.
- **Deps:** piston container in compose (dev) or Judge0 API key (prod);
  strict timeouts and network isolation.
- **Risks:** sandbox escape — never run user code on the host; enforce
  CPU/memory limits.

### 10.4 Gamification (XP, streaks, leaderboards)
- **Value:** retention.
- **Approach:** `user_progress` table (XP per evaluation score, daily streak
  counters), badge definitions, optional leaderboard endpoint (opt-in).
- **Deps:** new model + migration (Plan 03), APScheduler for streak resets.

### 10.5 OAuth (Google/GitHub) + account security
- **Value:** passwordless login, social sign-in.
- **Approach:** `authlib` OAuth2 client; link OAuth identities to existing
  accounts by verified email; add refresh-token rotation, password reset, and
  email verification flows.
- **Deps:** `authlib`, SMTP or SES for email, secrets in AWS Secrets Manager
  (per RECOMMENDATIONS.md deployment section).
- **Risks:** account takeover via unverified email matching — require verified
  email before linking.

### 10.6 Scheduling (APScheduler)
- **Value:** daily practice questions, session cleanup.
- **Approach:** background scheduler in the backend container; jobs: daily
  question email, expired-session cleanup, evaluation retention policy.
- **Deps:** `apscheduler`, persistent job store (SQLAlchemyJobStore).

## When to pick these up

After wave 2 lands and the CI/migration infrastructure (plans 02, 03) is in
place — each item then gets its own plan file derived from this one.
