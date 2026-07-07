# TalentLens — Phase 5, Sprint 5.2, Prompt 5
# Assessment Backend Foundation

Status: Implemented (models, repositories, services, router, migration, tests).
No AI, no transcription, no scoring, no Celery — pure CRUD persistence for
what the Candidate Assessment UI already collects client-side
(`AssessmentRunnerProvider`): aptitude answers, read-aloud recording metadata,
listen-and-repeat recording metadata.

---

## 0. Deliberate deviations from the Sprint 5.1 architecture blueprint

`docs/phase5-sprint5.1-assessment-management-architecture.md` designed a much
larger module (`Assessment`, `AssessmentTemplate`, `AssessmentQuestion`,
`AssessmentInvitation`, `RequireInvitationToken`, Celery beat, notifications).
None of that exists yet in the codebase, and this prompt explicitly scopes
this sprint down to "the minimum tables required for MVP." Two decisions
were made to reconcile the prompt's wording with what actually exists today:

1. **No `Invitation`/token entity.** The prompt asks `AssessmentSession` to
   store an "Invitation" and to authorize via a "Candidate Invitation Token,"
   but no such entity or token-issuance flow exists anywhere in the codebase
   (`OrganizationInvitation` is recruiter-org-onboarding only). Building a
   full signed-token candidate-auth primitive was judged out of scope for a
   "persistence foundation" prompt, so `AssessmentSession` links directly to
   `Campaign` + `Candidate` with no invitation FK.
2. **Recruiter-authenticated only.** Every endpoint here uses the existing
   `RequireRoles(RECRUITER, ORG_ADMIN, SUPER_ADMIN)` dependency — the same
   access model as `candidate_profile.py`'s notes/tasks/activity endpoints.
   There is no unauthenticated candidate-facing route yet. A real
   `RequireInvitationToken` primitive (per the 5.1 blueprint) is a follow-up
   sprint once the invitation-send flow itself is designed.

Everything else here reuses existing conventions exactly: Router → Service →
Repository → DB, `org_id`-scoped repository queries, `RequireRoles` RBAC,
Pydantic validation, `StorageBackend`-compatible relative storage paths.

---

## 1. Folder structure

```
backend/app/
├── models/
│   ├── assessment_session.py     # AssessmentSession, AssessmentSection, AssessmentSessionStatus
│   ├── assessment_answer.py      # AssessmentAnswer
│   └── assessment_recording.py   # AssessmentRecording, RecordingType, RecordingStatus
│
├── repositories/
│   ├── assessment_session.py     # AssessmentSessionRepository
│   ├── assessment_answer.py      # AssessmentAnswerRepository (upsert per question)
│   └── assessment_recording.py   # AssessmentRecordingRepository (upsert per recording type)
│
├── services/
│   └── assessment_session.py     # AssessmentSessionService — orchestrates all three
│
├── schemas/
│   └── assessment_session.py     # Create/Update/Response schemas for session/answer/recording
│
├── api/v1/endpoints/
│   └── assessment_sessions.py    # RequireRoles-gated router
│
└── api/v1/router.py               # registers assessment_sessions.router at /assessment/session

backend/alembic/versions/
└── a7b8c9d0e1f2_create_assessment_sessions.py

backend/tests/
├── test_assessment_session_service.py        # service unit tests (mocked repos)
├── test_assessment_sessions.py               # API tests (mocked service, RBAC coverage)
└── integration/
    └── test_assessment_sessions_integration.py  # real-Postgres full-stack lifecycle test
```

File naming follows the existing convention (bare domain noun per file; the
layer lives in the folder, the suffix lives in the class name) — no
`_service.py`/`_repository.py` suffixes.

---

## 2. Entity relationships

```
Organization (org_id, tenancy root)
   └── Campaign
         └── Candidate  (existing entity, org-scoped separately via organization_id)
               └── AssessmentSession   (unique per campaign_id + candidate_id)
                     ├── AssessmentAnswer[]      (unique per session_id + question_number)
                     └── AssessmentRecording[]   (unique per session_id + recording_type)
```

- `AssessmentSession` is the aggregate root for this module and carries
  `org_id` directly (denormalized from the owning Campaign, mirrors
  `Campaign`/`ScoringRule`) so every repository query is explicitly
  org-scoped without a join.
- `AssessmentAnswer` / `AssessmentRecording` scope through `session_id` only
  (no `org_id` column) — same shape as `CandidateTask`/`CandidateNote`
  hanging off `resume_file_id`.
- One `AssessmentSession` per `(campaign_id, candidate_id)` pair — a second
  `POST /assessment/session` for the same pair returns the existing session
  (resume semantics) rather than erroring or duplicating.
- One `AssessmentAnswer` per `(session_id, question_number)` and one
  `AssessmentRecording` per `(session_id, recording_type)` — both are
  upserted, so autosave/retake overwrites in place instead of accumulating
  history rows.
- `AssessmentRecording.storage_path` is a relative, `StorageBackend`-agnostic
  path computed at metadata-registration time
  (`assessment-recordings/{session_id}/{recording_type}/{uuid}{ext}`); no
  bytes are written in this sprint (`status` starts and stays `PENDING`).
  The upload endpoint due next sprint calls `StorageBackend.save()` at this
  exact path and flips `status` to `UPLOADED`/`FAILED`.

---

## 3. Endpoint list

All under `RequireRoles(RECRUITER, ORG_ADMIN, SUPER_ADMIN)`, prefix
`/api/v1/assessment/session`:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/assessment/session` | Create a session for `{campaign_id, candidate_id}`, or return the existing one (resume) |
| `GET` | `/assessment/session/{id}` | Fetch a session |
| `PATCH` | `/assessment/session/{id}` | Update `current_section`/`current_question` progress |
| `POST` | `/assessment/session/{id}/answers` | Upsert one aptitude answer (`question_number` 1–5) |
| `POST` | `/assessment/session/{id}/recordings` | Upsert recording metadata (no audio bytes) |
| `POST` | `/assessment/session/{id}/complete` | Mark the session `COMPLETED` (idempotent) |

Validation: `question_number` bounded 1–5 at the schema layer; `PATCH`/answer/
recording all 422 once a session is `COMPLETED`; `campaign_id`/`candidate_id`
must belong to the caller's org (404 otherwise, never leaks cross-org
existence).

---

## 4. How the frontend will integrate next sprint

`AssessmentRunnerProvider` (`frontend/src/features/candidate-runner/`) is
currently pure client-side React state — the aptitude `answers` record, the
`readAloudRecording`/`listenRepeatRecording` blobs, and completion flags never
leave the browser. Wiring it to this backend means:

1. On runner mount, call `POST /assessment/session` with the campaign/
   candidate identifiers already known to the recruiter dashboard context,
   and seed `AssessmentRunnerProvider`'s state from the response
   (`current_section`, `current_question`) instead of always starting fresh.
2. Debounce `setAnswer` to `POST /assessment/session/{id}/answers` (the same
   upsert-per-question-number shape the provider already tracks via
   `Record<number, string>`).
3. After each device-check-gated recording completes, call
   `POST /assessment/session/{id}/recordings` with filename/mime_type/
   duration/file_size metadata — **not** the audio blob itself; the actual
   upload call is a separate endpoint landing next sprint.
4. On final submit, call `POST /assessment/session/{id}/complete`.
5. This all still runs through the authenticated recruiter/dashboard
   session in this sprint (see §0) — a genuinely candidate-facing,
   unauthenticated runner (matching the `(candidate-assessment)` route
   group's intent) needs the invitation/token follow-up first.

---

## 5. Explicitly deferred (per prompt instructions)

No Whisper, no transcript generation, no AI scoring, no Celery workers, no
audio byte upload endpoint, no `AssessmentInvitation`/token auth, no
`AssessmentTemplate`/`AssessmentQuestion` (question set is currently the
fixed 5-question aptitude section the frontend already hardcodes). These are
tracked as future-sprint seams, not gaps in this one.
