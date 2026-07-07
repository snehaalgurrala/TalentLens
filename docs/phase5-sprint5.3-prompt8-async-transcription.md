# TalentLens — Phase 5, Sprint 5.3, Prompt 8
# Asynchronous Speech Transcription Pipeline

Status: Implemented. Recording upload now automatically queues a Celery task
that loads the audio via `StorageBackend`, transcribes it with the existing
`SpeechService` (local Whisper), and persists the result to a new
`AssessmentTranscript` row — all off the request path. No communication
scoring, no transcript comparison, no recruiter reports, no Resume AI
changes; this prompt only wires transcription end-to-end and makes it
retrievable.

```
Candidate → Browser Recording → Upload API → StorageBackend → AssessmentRecording
                                                                     │
                                                                     ▼
                                                            Celery Queue
                                                                     │
                                                                     ▼
                                                            SpeechService
                                                                     │
                                                                     ▼
                                                            WhisperService
                                                                     │
                                                                     ▼
                                                          AssessmentTranscript
```

---

## 1. Architecture

```
backend/app/
├── models/assessment_transcript.py     # AssessmentTranscript, TranscriptStatus
├── repositories/assessment_transcript.py
├── services/assessment_transcript.py   # create/start/complete/fail/get/retry — no Whisper imports
├── workers/speech_transcription.py     # transcribe_recording Celery task
├── schemas/assessment_transcript.py    # AssessmentTranscriptResponse
└── api/v1/endpoints/
    ├── assessment_sessions.py          # upload endpoint now dispatches the task
    └── assessment_transcripts.py       # GET /assessment/transcripts/{recording_id}
```

This is a straight structural copy of the resume/job-description parsing
pipeline (`app/workers/resume_parser.py`, `app/workers/job_description_parser.py`,
`app/workers/embedding_worker.py`) applied to speech instead of text
extraction, using the `SpeechService` primitive built in
`docs/phase5-sprint5.3-prompt7-speech-ai-foundation.md`. No new architectural
pattern was introduced — every layer below follows an existing precedent
file exactly.

### Layering rules preserved

- **Routers never touch AI or Celery internals directly.** The upload router
  (`assessment_sessions.py`) only calls `_enqueue_transcription(str(recording.id))`
  — a plain `.delay()` wrapper with a lazy import, identical in shape to
  `resumes.py`'s `_enqueue_parse`. Celery is never imported at router module
  load time.
- **Services never import Whisper or Celery tasks at module scope.**
  `AssessmentTranscriptService` only depends on `AssessmentTranscriptRepository`.
  Its one exception, `retry_failed()`, lazily imports the Celery task inside a
  function body (`_default_dispatcher`), exactly like `resumes.py`'s pattern —
  never at import time.
- **Only `app/workers/speech_transcription.py` calls `SpeechService`.** No
  other module in this sprint imports `app.ai.speech.*`.

---

## 2. Entity: `AssessmentTranscript`

Kept **separate** from `AssessmentRecording`, which continues to store upload
metadata only (`app/models/assessment_recording.py` is unchanged).

| Column | Type | Notes |
|---|---|---|
| `id` | `Uuid`, PK | |
| `organization_id` | `Uuid`, FK → `organizations.id` | Denormalized from the recording's owning session (`AssessmentSession.org_id`) at creation time, so the read endpoint can scope by org without joining through `assessment_recordings → assessment_sessions` on every request. |
| `recording_id` | `Uuid`, FK → `assessment_recordings.id`, **unique** | One transcript per recording. |
| `status` | `Enum(TranscriptStatus)` | `PENDING` → `PROCESSING` → `COMPLETED` \| `FAILED` |
| `transcript` | `Text`, nullable | Set on `COMPLETED` |
| `language` | `String(16)`, nullable | Whisper's detected language, e.g. `"en"` |
| `model_name` | `String(64)`, nullable | e.g. `"base"` |
| `processing_time_ms` | `Integer`, nullable | Wall-clock Whisper time |
| `segment_count` | `Integer`, nullable | |
| `error_message` | `String(1000)`, nullable | Set on `FAILED`, truncated to 1000 chars |
| `created_at` / `updated_at` | `DateTime(timezone=True)` | |

Migration: `alembic/versions/c1d2e3f4a5b6_create_assessment_transcripts.py`
(`down_revision = "b4c5d6e7f8a9"`, the pre-existing head). Follows the
project's established Enum + `create_table` rule exactly: the
`transcriptstatus` enum is passed directly into the column definition and
**never** `.create()`-d separately (see the recorded fix in
`a7b8c9d0e1f2_create_assessment_sessions.py` — calling `.create()` before
`create_table` with asyncpg raises `DuplicateObjectError` because
`create_table`'s own DDL already emits `CREATE TYPE`).

---

## 3. Celery flow (`app/workers/speech_transcription.py`)

Phase-based, mirroring `resume_parser.py` exactly:

1. **Phase 1** (DB transaction) — fetch the `AssessmentRecording` joined to
   its owning `AssessmentSession.org_id` (no repository method needed org_id
   up front, same trick as `resume_parser._get_campaign_org_id`).
   Idempotently create-or-fetch the `AssessmentTranscript` row
   (`service.create_pending`). If it's already `COMPLETED`, skip everything
   else (safe against a duplicate `.delay()` or a retried task). Otherwise
   mark `PROCESSING` and commit.
2. **Phase 2** (no DB) — `StorageBackend.load(recording.storage_path)` reads
   the audio bytes. Storage is never touched directly by disk path — this
   keeps the pipeline correct if `StorageBackend` later becomes S3, with
   zero code changes here.
3. **Phase 3** (no DB) — `SpeechService.transcribe(audio_bytes, mime_type=..., filename=...)`.
   No Whisper import in this file — `speech_transcription.py` only knows
   `SpeechService`'s public interface.
4. **Phase 4** (DB transaction) — persist `transcript` / `language` /
   `model_name` / `processing_time_ms` / `segment_count`, mark `COMPLETED`,
   commit.

Registered in `celery_app.py`'s `include=[...]` list alongside the other
three worker modules.

### Dispatch

`assessment_sessions.upload_assessment_recording` calls
`_enqueue_transcription(str(recording.id))` immediately after
`service.upload_recording(...)` returns successfully. The upload request
itself never waits on transcription — the HTTP response returns as soon as
the audio bytes are durably stored and the recording row is marked
`UPLOADED`.

---

## 4. Retry strategy

| Failure | Classification | Behavior |
|---|---|---|
| `AudioValidationError` (missing/unsupported/oversized audio) | Permanent | No retry — logged and re-raised; transcript marked `FAILED` |
| `ModelLoadError`, `TranscriptionError`, any other exception | Transient | Retried up to **3** times with exponential backoff: 30 s, 60 s, 120 s (`30 * 2**retries`, identical formula to every other worker in this codebase) |

`_mark_failed` runs `AssessmentTranscriptService.fail_processing` in the
**same** coroutine/event loop as the main work (via
`_run_transcribe_recording_with_recovery`), not as a second, separate
`asyncio.run()` call — see `celery_app.run_task`'s docstring for why a second
call is unsafe (a pooled asyncpg connection checked back in at the end of one
event loop is unusable by the next, closed loop). `fail_processing` is a
best-effort no-op if the transcript row somehow doesn't exist yet, and never
masks the original exception (it's wrapped in its own `try/except`).

### Manual retry (service-level, no API endpoint)

`AssessmentTranscriptService.retry_failed(recording_id, user)` resets a
`FAILED` transcript back to `PENDING` and re-dispatches the Celery task. It
is **not** exposed via an API route this sprint (per spec: "Do NOT expose a
transcription trigger endpoint") — it exists purely as a service capability,
exercised directly in `tests/test_assessment_transcript_service.py`, for a
future admin/ops surface to call.

---

## 5. Failure recovery

- A crashed Phase 1 (recording or org lookup fails) leaves nothing behind —
  there's no transcript row yet, so nothing needs cleanup.
- A crash between Phase 1 and Phase 4 (e.g. Whisper OOMs, ffmpeg missing)
  leaves the transcript `PROCESSING`. Celery's own retry re-invokes the task,
  which re-fetches the recording, sees the transcript isn't `COMPLETED`, and
  re-runs Phases 2–4 from scratch (transcription is naturally idempotent —
  re-transcribing the same stored audio bytes produces the same result).
- After 3 exhausted retries (or a permanent `AudioValidationError`), the
  transcript is left `FAILED` with `error_message` populated, and
  `GET /assessment/transcripts/{recording_id}` reports that state to the
  caller instead of hanging indefinitely.

---

## 6. API

```
GET /api/v1/assessment/transcripts/{recording_id}
```

Read-only. Same RBAC as the session endpoints (`RECRUITER`, `ORG_ADMIN`,
`SUPER_ADMIN` — candidates have no platform account yet). Returns 404 until
a transcript row exists for that recording, and 404 (not 403) if the
recording belongs to a different organization — `AssessmentTranscriptService.get_transcript`
checks `transcript.organization_id == user.org_id` directly against the
denormalized column, so no join through `assessment_recordings` is needed to
enforce org isolation.

No trigger/create endpoint exists — transcription is queued automatically
by the upload endpoint, per spec.

---

## 7. Frontend

No UI changes. The upload flow (browser recording → upload API) already
completes and returns before this sprint's Celery dispatch runs, so no
frontend change was needed to "tolerate background processing" — the
recording upload response shape is unchanged, and transcription happens
entirely after the HTTP response is sent.

---

## 8. Explicitly deferred

No communication/pronunciation scoring, no transcript comparison against a
reference reading, no recruiter-facing transcript UI, no Resume AI changes,
no transcription-trigger API endpoint. This sprint's only deliverable is:
upload → automatic background transcription → retrievable read-only result.

---

## 9. Future WhisperX compatibility

`SpeechService.transcribe()` already returns a stable `TranscriptionResult`
(transcript, language, per-segment timing/confidence) independent of the
underlying engine (`app/ai/speech/speech_service.py`). Swapping
`WhisperService`'s local `openai-whisper` for WhisperX (word-level
timestamps, better diarization) is confined entirely to
`app/ai/speech/whisper_service.py` — `speech_transcription.py`,
`AssessmentTranscriptService`, and the `AssessmentTranscript` schema would
need no changes, since they only depend on `SpeechService`'s public
`TranscriptionResult` contract, not on Whisper's raw internals. If WhisperX's
richer alignment output is later persisted (e.g. word-level timestamps),
that's an additive column on `AssessmentTranscript` behind a new migration,
not a rewrite of this pipeline.

---

## 10. Testing

- `backend/tests/test_assessment_transcript_service.py` — repository mocked,
  exercises `create_pending` (idempotent), `start_processing`,
  `complete_processing`, `fail_processing` (incl. 1000-char truncation and
  missing-row no-op), `get_transcript` (org scoping, 404s), and
  `retry_failed` (rejects non-`FAILED` transcripts, resets + dispatches on
  `FAILED`).
- `backend/tests/test_speech_transcription_worker.py` — mirrors
  `test_job_description_parser.py`'s structure exactly: every collaborator
  (`AssessmentTranscriptRepository`, `AssessmentTranscriptService`) is
  patched, `SpeechService`/`StorageBackend` are injected via the
  `_speech_service` / `_storage` keyword overrides on
  `_run_transcribe_recording`, and `asyncio.run` is patched directly to
  verify the Celery task wrapper's retry/backoff math
  (`30 * 2**retries`) and permanent-vs-transient error classification. No
  real Whisper model is loaded.
- `backend/tests/test_assessment_transcripts.py` — API tests for the read
  endpoint (`AssessmentTranscriptService` mocked via dependency override),
  covering completed/pending payload shapes, 404, and RBAC (`CANDIDATE`
  forbidden).
- `backend/tests/test_assessment_sessions.py` — extended
  `TestUploadRecording` with an autouse `_enqueue_transcription` patch (same
  shape as `test_resumes.py`'s `_no_celery` fixture) plus two new tests
  asserting the transcription task is dispatched after a successful upload
  and *not* dispatched when the upload itself fails.
- `backend/tests/integration/test_assessment_transcript_integration.py` —
  real-Postgres tests (same disposable-database caveat as every other file
  under `tests/integration/`): exercises `AssessmentTranscriptRepository`
  directly, and runs `_run_transcribe_recording`'s full async body against a
  real database with `SpeechService`/`StorageBackend` swapped for fakes — no
  real Whisper model is ever loaded, per the project's testing rule.

Verified before completion: `ruff check` clean, `mypy` clean (`strict =
false`, `ignore_missing_imports = true`), and the full
`pytest tests --ignore=tests/integration` suite passes with no regressions.
