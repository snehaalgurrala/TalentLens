# TalentLens — Phase 5, Sprint 5.7, Prompt 13A
# Assessment Invitation Backend + SMTP Foundation

Backend-only foundation for inviting candidates to take an assessment by
email: a new `AssessmentInvitation` model, a token-secured public lookup
endpoint, a recruiter-facing bulk-send endpoint, and an SMTP email delivery
abstraction. No recruiter UI, no candidate assessment UI changes — those are
future sprints that will consume the two endpoints added here.

```
Recruiter                                    Candidate
    │  POST /assessment/invitations/send          │
    │  {campaign_id, candidate_ids[], expiration}  │
    ▼                                              │
AssessmentInvitationService                        │
    │  create/resume AssessmentSession              │
    │  create/update AssessmentInvitation (PENDING) │
    │  EmailService.send_assessment_invitation()    │
    │        └─► SMTPProvider (smtplib)             │
    ▼                                              │
  mark_sent() → SENT                    email: "Begin Assessment" → /assessment/start/{token}
                                                    │
                                                    ▼
                                    GET /assessment/invitations/{token}
                                                    │
                                    validate (not expired/revoked/completed)
                                    PENDING/SENT → mark_opened() → OPENED
                                                    ▼
                                    { assessment_session, campaign, candidate_display_name, status, expires_at }
```

## 1. Model: `AssessmentInvitation`

`app/models/assessment_invitation.py` — one row per `AssessmentSession`
(`UniqueConstraint`/unique index on `assessment_session_id`): resending an
invitation updates the existing row with a fresh token and expiry rather than
creating a second one, so "one active invitation per session" is enforced at
the schema level, not just in application logic.

Only `token_hash` (SHA-256 hex digest, via the existing
`app.core.security.hash_token`/`generate_invitation_token` helpers) is
persisted — the same pattern already used by `OrganizationInvitation` and
`User.refresh_token_hash`. The raw token exists only in the emailed URL and
is never written to the database, so a database read (or leak) alone can
never grant assessment access.

`AssessmentInvitationStatus`: `PENDING → SENT → OPENED → STARTED → COMPLETED`,
with `EXPIRED`/`REVOKED` as terminal side-exits. This sprint only drives the
lifecycle as far as `OPENED`; `STARTED`/`COMPLETED` transitions
(`AssessmentInvitationRepository.mark_started`/`mark_completed`) are wired up
into the repository/service now so a future sprint that lets a candidate
actually take the assessment via `{token}` can call them without another
migration.

Migration: `alembic/versions/75235da0bde6_create_assessment_invitations.py`
— adds `assessment_invitations` with `CASCADE` foreign keys to
`organizations`, `assessment_sessions`, `candidates`, and `campaigns` (so the
invitation is cleaned up automatically if any parent row is deleted).

## 2. Repository

`AssessmentInvitationRepository` (`app/repositories/assessment_invitation.py`)
follows the existing create/update-plus-refresh convention (see
`OrganizationInvitationRepository`, `CommunicationAssessmentRepository`).
`mark_sent`/`mark_opened`/`mark_started`/`mark_completed`/`expire`/`revoke`
are thin wrappers over the generic `update()` that also stamp the matching
`*_at` timestamp — kept as named methods (rather than inlined `update()`
calls at every call site) because each name documents which lifecycle edge is
legal, which the tests exercise directly.

## 3. Service: token lifecycle and per-candidate send results

`AssessmentInvitationService` (`app/services/assessment_invitation.py`) owns
two flows:

**`send_invitations`** (recruiter-facing): validates the campaign once,
then loops candidates independently. A per-candidate failure (candidate not
in the organization, candidate has no email on file, already-completed
invitation, or an SMTP exception) is caught as an internal
`_SendFailureError` and recorded in the response's `failed` list — it never
aborts the batch. Session creation reuses
`AssessmentSessionRepository.get_by_campaign_and_candidate`/`create` exactly
as `AssessmentSessionService.create_or_resume` does, so an invitation never
creates a duplicate session for a campaign/candidate pair.

**`get_invitation_by_token`** (candidate-facing, public): looks up by
`hash_token(token)`, lazily transitions `PENDING`/`SENT`/`OPENED` invitations
past their `expires_at` into `EXPIRED` on read (no background job — nothing
short-lived depends on the transition happening before the next read), then
rejects `REVOKED`/`EXPIRED`/`COMPLETED` with `410 Gone`. A valid
`PENDING`/`SENT` invitation is advanced to `OPENED`; an already
`OPENED`/`STARTED` invitation is left alone (idempotent — opening the link
twice doesn't regress progress).

Neither `candidate_id`, `campaign_id`, nor `assessment_session_id` ever
appears in a URL — the only public identifier is the opaque token, exactly
per the token requirements in this sprint's spec. They do appear in the JSON
body returned by `GET /assessment/invitations/{token}` (nested under
`assessment_session`/`campaign`), which the spec requires so the candidate
frontend has something to render and, eventually, resume against.

## 4. Email architecture (`app/services/email/`)

| File | Responsibility |
|---|---|
| `email_service.py` | `EmailProvider` (ABC — the swap point) + `EmailService`, which renders `templates/assessment_invitation.{html,txt}` via `string.Template` (`$placeholder` substitution — no Jinja2 dependency added) and calls `provider.send(...)`. |
| `smtp_provider.py` | `SMTPProvider(EmailProvider)` — the only implementation today. Builds a `multipart/alternative` message (plain-text part first, HTML second, per RFC 2046) and sends it via stdlib `smtplib`. |
| `templates/assessment_invitation.html` / `.txt` | Branded HTML + plain-text fallback: greeting, campaign name, duration placeholder, expiration, "Begin Assessment" button/link, support footer. |

**Why `asyncio.to_thread` instead of an async SMTP library:** `smtplib` is
blocking and `aiosmtplib` is not in `requirements.txt`. Rather than add a new
dependency for one call site, `SMTPProvider.send` pushes the blocking call
onto a worker thread. If invitation volume ever grows enough for this to
matter, swapping in a real async provider (see below) is a one-file change.

**Future provider replacement:** implement a new `EmailProvider` subclass
(e.g. `SendGridProvider`, `SESProvider`) in a sibling module, then change the
one construction site —
`get_assessment_invitation_service()` in
`app/api/v1/endpoints/assessment_invitations.py`, currently
`EmailService(SMTPProvider())` — to the new provider. Nothing in
`AssessmentInvitationService` or the templates needs to change, since both
only depend on the `EmailProvider.send(to_email, subject, html_body,
text_body)` abstraction.

## 5. Configuration (`app/core/config.py`)

New settings, all read from the environment (see `.env.example`):
`FRONTEND_BASE_URL` (used to build `{FRONTEND_BASE_URL}/assessment/start/{token}`),
`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`,
`SMTP_FROM_NAME`, `SMTP_TLS`, `SMTP_SSL`.

## 6. API

New router `app/api/v1/endpoints/assessment_invitations.py`, mounted at
`/api/v1/assessment/invitations`:

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/send` | `RequireRoles(RECRUITER, ORG_ADMIN, SUPER_ADMIN)` | Body: `campaign_id`, `candidate_ids[]` (1–200), `expiration_hours` (1–2160). Returns `{succeeded: [{candidate_id, invitation_id}], failed: [{candidate_id, reason}]}` — always `201` even with partial failures, since the response body already encodes per-candidate outcome. |
| GET | `/{token}` | none (public) | Same access model as any emailed magic link — security comes entirely from the token's entropy (`secrets.token_urlsafe(32)`, 256 bits), not from a session/RBAC check. Returns `404` if the token doesn't exist, `410` if expired/revoked/completed. |

## 7. Tests

- `tests/test_assessment_invitation_repository.py` — CRUD + every lifecycle
  transition, against a fake `AsyncSession` (no DB), mirroring
  `test_communication_assessment_repository.py`.
- `tests/test_assessment_invitation_service.py` — send flow (new session,
  resend, candidate-not-found, no-email, already-completed, SMTP failure)
  and token flow (not-found, revoked, completed, lazy expiration, opened
  transition, idempotent re-open), all repos/EmailService mocked.
- `tests/test_assessment_invitations_api.py` — RBAC on `/send` (recruiter
  succeeds, `CANDIDATE` role gets `403`), validation (`422` on empty
  candidate list / non-positive expiration), and that `GET /{token}` needs
  no `get_current_user` override to succeed.
- `tests/test_email_service.py` — `EmailService` template rendering (no
  leftover `$placeholders`) against a fake `EmailProvider`; `SMTPProvider`
  against a mocked `smtplib.SMTP` (starttls/login only when configured,
  correct MIME structure) — no real network connection in any test.

All new/modified files pass `ruff check` (`select = ["E", "F", "I", "N",
"UP", "W"]`). The full non-integration suite (`pytest tests/
--ignore=tests/integration`) passes with no regressions. The migration was
also applied and reversed against the local dev Postgres container
(`alembic upgrade head` / `downgrade -1` / `upgrade head`) to confirm the
DDL and cascade FKs are correct beyond what SQLite/mocked tests can verify.

## 8. Explicitly out of scope (per this sprint's brief)

- Recruiter UI for sending invitations or viewing their status.
- Any change to the candidate assessment-taking UI or flow.
- Wiring `mark_started`/`mark_completed`/`revoke` into an endpoint — the
  repository/service support exists, but nothing calls them yet because
  there is no candidate-facing "start assessment via token" endpoint in this
  sprint. **Superseded in Sprint 5.7 Prompt 13B**, which adds
  `POST /assessment/invitations/{token}/start` and `.../complete` — see
  `docs/phase5-sprint5.7-prompt13b-invitation-ui.md`. `revoke` remains
  unwired (no revoke UI exists yet).
- Per-campaign assessment duration — the email shows a fixed placeholder
  string (`"Approximately 20-30 minutes"`) since no `AssessmentTemplate`/
  duration field exists on `Campaign` yet.
