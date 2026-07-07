# TalentLens — Phase 5, Sprint 5.2, Prompt 6
# Real Audio Upload Pipeline

Status: Implemented (backend upload endpoint + migration + tests, frontend
session wiring + real upload UI + tests). No Whisper, no transcript
generation, no AI scoring, no Celery — this prompt only gets the two recorded
audio clips from the candidate's browser into `StorageBackend` and marks the
corresponding `AssessmentRecording` row `UPLOADED`.

---

## 0. What changed vs. Prompt 5

`docs/phase5-sprint5.2-prompt5-assessment-backend-foundation.md` built the
session/answer/recording-metadata persistence layer but explicitly deferred
"no audio byte upload endpoint" (§5) and noted the frontend "still runs
through the authenticated recruiter/dashboard session" with no session id
ever wired into `AssessmentRunnerProvider` (§4). This prompt closes both
gaps at the minimum scope needed to make uploads actually work end-to-end:

1. **New self-sufficient upload endpoint.** `POST /assessment/session/{id}/recordings/{recording_type}/upload`
   validates the multipart upload, saves the bytes via `StorageBackend`, and
   upserts the full `AssessmentRecording` row (metadata + `status=UPLOADED` +
   a new `uploaded_at` timestamp) in one call. It does not require the
   Prompt 5 metadata-only endpoint (`POST /{id}/recordings`) to have run
   first — that endpoint is unchanged and still available for metadata-only
   registration.
2. **Minimal session-id plumbing on the frontend.** The candidate runner
   previously had no `session_id` anywhere — not even a way to create one.
   The landing screen now reads `campaign_id`/`candidate_id` from the URL
   query string and calls the existing `POST /assessment/session`
   (create-or-resume) once, storing the result in
   `AssessmentRunnerProvider`. This is intentionally minimal: no invitation
   token, no candidate-specific auth — the recruiter-authenticated model from
   Prompt 5 is unchanged (see §3).

---

## 1. Backend changes

```
backend/app/
├── models/assessment_recording.py    # + uploaded_at: datetime | None
├── schemas/assessment_session.py     # + AssessmentRecordingResponse.uploaded_at
├── services/assessment_session.py    # + storage dependency, upload_recording(),
│                                        _build_recording_storage_path() shared helper,
│                                        _validate_recording_mime_type/_size
└── api/v1/endpoints/assessment_sessions.py
                                       # + StorageDep, POST /{id}/recordings/{recording_type}/upload

backend/alembic/versions/
└── b4c5d6e7f8a9_add_uploaded_at_to_assessment_recordings.py

backend/tests/
├── test_assessment_session_service.py   # + TestUploadRecording (mocked storage/repos)
├── test_assessment_sessions.py          # + TestUploadRecording (mocked service, multipart POST)
└── integration/test_assessment_sessions_integration.py
                                          # + TestUploadRecordingPersistence (real Postgres + disk,
                                            written but NOT run — see file docstring)
```

### Validation

- Mime type: exactly `audio/webm` or `audio/ogg` (any `;codecs=...` suffix is
  stripped before comparing) — anything else is rejected with 422.
- Size: 10 MB hard cap (`_MAX_RECORDING_UPLOAD_MB` in `assessment_session.py`,
  distinct from the unrelated `MAX_RECORDING_SIZE_MB = 50` sanity ceiling
  that only guards the Prompt 5 metadata-only endpoint's *claimed*
  `file_size` before any bytes exist).
- Empty upload, missing session, and completed-session are all rejected
  before any repository write — a rejected upload never leaves a row behind
  or partially-written bytes.

### Lifecycle

```
PENDING  --[POST /{id}/recordings]-->  PENDING (metadata only, unchanged from Prompt 5)
PENDING  --[POST /{id}/recordings/{type}/upload, success]-->  UPLOADED (+ uploaded_at set)
     *   --[POST /{id}/recordings/{type}/upload, validation failure]-->  4xx, no row written/changed
```

`RecordingStatus.FAILED` is defined but **not actually reachable** through
this endpoint yet — every validation failure this sprint happens before any
database write, so there is no row transitioning into `FAILED`. This is a
known asymmetry: `FAILED` is reserved for a future asynchronous failure path
(e.g. a background re-encode step) that doesn't exist yet.

### StorageBackend integration

No new abstraction — `upload_recording()` takes the same `StorageBackend`
already injected into `ResumeFileService` (`app.storage.factory.get_storage_backend`,
currently `LocalStorageBackend` under `settings.LOCAL_STORAGE_PATH`). Swapping
to S3/MinIO in production is a factory-level change only; nothing in the
service or endpoint layer needs to change.

---

## 2. Frontend changes

```
frontend/src/
├── types/assessment-session.types.ts        # AssessmentSession(Create), AssessmentRecording,
│                                               RecordingType, backend RecordingStatus
├── services/assessment-session.service.ts    # createOrResumeSession, uploadRecording (FormData)
├── hooks/use-assessment-session.ts           # useCreateOrResumeSession, useUploadRecording
└── features/candidate-runner/
    ├── types.ts                              # + RecordingUploadStatus, RecordingUploadState
    │                                           (client-local progress state, distinct from both
    │                                            the recorder's own RecordingStatus in this file
    │                                            and the backend's RecordingStatus above)
    ├── assessment-runner-context.tsx         # + sessionId, readAloudUpload/listenRepeatUpload
    ├── landing-screen.tsx                    # reads campaign_id/candidate_id from the URL,
    │                                           creates/resumes the session once
    └── uploading-screen.tsx                  # real per-recording upload + progress + retry,
                                                replaces the old 4-stage setTimeout simulation
```

The uploading screen no longer fakes "Generating Transcript" / "Evaluating
Communication" / "Preparing Report" stages — those were always fictional
placeholders for work this sprint explicitly excludes. It now shows two real
rows (Read Aloud, Listen & Repeat), each with its own upload progress and a
Retry button that appears only on failure. A failed upload never discards the
recording — the `Blob`/object URL stay in `AssessmentRunnerProvider` exactly
as before, so Retry just re-arms the upload without re-recording.

---

## 3. Explicitly deferred (unchanged from Prompt 5, now narrower)

No Whisper, no transcript generation, no AI scoring, no Celery workers.
Still no `AssessmentInvitation`/token-based candidate auth — every call in
this pipeline (including the new upload endpoint) is recruiter-authenticated
via `RequireRoles(RECRUITER, ORG_ADMIN, SUPER_ADMIN)`, unchanged from Prompt
5. The session id now exists and is wired end-to-end, but "candidate takes
the assessment unauthenticated from an email link" is still a follow-up
sprint once the invitation/token flow itself is designed.
