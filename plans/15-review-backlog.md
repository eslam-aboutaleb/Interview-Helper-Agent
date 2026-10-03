# Plan 15 — Review backlog (deferred items)

- **Wave:** 5 — documentation only; **do not execute** in this cycle
- **Depends on:** wave 4
- **Priority:** P2 — captured from the 2026-10-03 code review

## Objective

Record the review findings that need design or infra work before they can
be scheduled, with enough detail that a future cycle can pick them up
without re-doing the analysis. No code in this plan.

## Items

### 15.1 PII encryption at rest (L5)

- **Finding:** full resume/JD text and the parsed email address are stored
  plaintext in `UserDocument.content_text` / `parsed_metadata`
  (`routes/documents.py` 48–54, `services/document_service.py` 202–204).
- **Approach:** application-level encryption (e.g. `cryptography` Fernet
  with the key in AWS Secrets Manager) or Postgres TDE/`pgcrypto`;
  minimize stored fields; keep the API scoped to the owning user (already
  enforced via `user_id` filters).
- **Deps:** key management + rotation policy, migration strategy for
  existing rows, decision on searchable-encrypted vs. plaintext email.
- **Risks:** key loss = data loss; search over encrypted text needs
  blind indexes.

### 15.2 skill-gap verb change (L7)

- **Finding:** `POST /api/documents/skill-gap` is a read-only computation
  with IDs in the query string (visible in access logs); semantically a GET.
- **Approach:** add `GET /api/documents/skill-gap?resume_id=&jd_id=` and
  deprecate the POST route (dual-route deprecation), or switch outright
  with a coordinated frontend change (`documentsApi.skillGap` in
  `services/api.ts`).
- **Deps:** coordination with plan 12 (owns `api.ts`); decide whether any
  proxy/log policy requires the change.
- **Risks:** breaking change for existing clients — prefer dual-route
  deprecation over a hard switch.

### 15.3 Anonymous-generation product decision (H1 alternative)

- **Finding:** plan 11 gates `POST /questions/generate` behind auth. If
  anonymous generation is an intentional product requirement, the
  alternative is to keep it open **and** document it explicitly + add
  rate-limiting (e.g. per-IP token bucket on the generate route).
- **Deps:** product decision; rate-limit middleware (e.g. slowapi).

### 15.4 Already fixed (no action)

- **M6** (unbounded document upload) — fixed in commit `edb4d72`:
  `MAX_UPLOAD_BYTES = 10 MiB` in `routes/documents.py`, returns 413.

## When to pick these up

After wave 4 lands — 15.1 needs the Secrets Manager setup from the
deployment checklist; 15.2 and 15.3 are one-line decisions plus small PRs.
