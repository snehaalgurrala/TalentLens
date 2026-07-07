# TalentLens — Phase 5, Sprint 5.6, Prompt 12
# Recruiter Assessment Dashboard

Exposes the assessment pipeline built in Sprints 5.3–5.5 (recording upload →
Whisper transcription → Read Aloud / Listen & Repeat analysis → aggregate
`CommunicationAssessment`) to recruiters through a read-only dashboard. No AI
logic, scoring, or navigation chrome changed — this sprint is entirely
presentation plus the minimal read endpoints needed to reach it.

```
Candidate profile ("Assessment" tab)
        │  GET /assessment/session/by-candidate/{candidate_id}?campaign_id=
        ▼
  Assessment session found? ──no──► "Assessment not started" empty state
        │ yes
        ▼
"View Full Assessment" → /assessments/{sessionId}
        │  GET /assessment/session/{id}/full
        ▼
  AssessmentDashboardView (10 sections)
        │  GET /assessment/session/{id}/recordings/{type}/download (audio only)
        ▼
  <audio controls>
```

## 1. Why three new backend endpoints

The dashboard needs, per session: the session row, up to two recordings, each
recording's transcript and analysis, the aggregate communication assessment,
and playable audio. Before this sprint:

- There was no way to discover a session id from a candidate id without
  calling the create-or-resume `POST`, which would incorrectly create a
  session just from viewing a profile.
- There was no way to discover recording/transcript/analysis ids from a
  session id — `AssessmentRecordingRepository.list_by_session` existed but
  was never wired to a route, so a client had no path from "session id" to
  "recording id" other than the response of an upload call.
- There was no endpoint that streamed recording audio bytes back (only
  `POST .../upload` existed).

Three small, additive endpoints close these gaps — all thin wrappers over
existing repository methods/services, added to the existing
`assessment_sessions.py` router (prefix `/assessment/session`):

| Method | Path | Purpose |
|---|---|---|
| GET | `/by-candidate/{candidate_id}?campaign_id=` | Read-only session lookup for the candidate-profile entry point. Wraps the existing `AssessmentSessionRepository.get_by_campaign_and_candidate`. Registered **before** `GET /{id}` so the literal `by-candidate` segment isn't captured by the `{id}: UUID` path parameter. |
| GET | `/{id}/full` | The one aggregation endpoint — composes session + both recordings (each with nested transcript, analysis, and reference sentence) + communication assessment into a single response, avoiding up to 8 sequential round trips. |
| GET | `/{id}/recordings/{recording_type}/download` | Streams recording audio bytes, mirroring the existing `GET /resumes/{resume_id}/download` pattern (`storage.load(path)` → `Response(media_type=...)`). |

New files: `app/schemas/assessment_dashboard.py`, `app/services/assessment_dashboard.py`.
No new tables, no Alembic migration — purely composition of existing rows.

Reference sentences (`AssessmentRecordingDetail.reference_sentence`) are read
from the same fixed global settings (`get_read_aloud_reference_sentence()` /
`get_listen_repeat_reference_sentence()`) the analysis pipeline itself uses —
they're not stored per-analysis today (there's no per-campaign assessment-content
model yet), so the dashboard surfaces the same source of truth rather than
duplicating the text as a frontend constant.

## 2. Navigation entry point

There was previously no in-app way to reach an assessment session at all
(candidates only reach it via an emailed link with `?campaign_id=&candidate_id=`
query params). To make the dashboard reachable without redesigning navigation:

- A new **"Assessment"** tab was added to the existing candidate profile tabs
  (`frontend/src/features/candidate-profile/candidate-profile-view.tsx`),
  following the same pattern as every other tab (own query, own loading/error/empty
  states). It looks up the session via `by-candidate` using `profile.campaign.id` +
  the candidate id, and shows either an empty state or a compact summary with a
  "View Full Assessment" link.
- The dashboard itself lives at a new leaf route,
  `frontend/src/app/(dashboard)/assessments/[sessionId]/page.tsx`, under the
  route group that already has "Assessments" registered in the sidebar
  (`frontend/src/layouts/nav-items.tsx`) — no nav change needed. The existing
  `/assessments` stub page (assessment-configuration placeholder) is untouched.

## 3. Page architecture

```
AssessmentDashboardPage (server component, awaits [sessionId])
  └─ AssessmentDashboardView (client, useAssessmentSessionFull(sessionId))
       ├─ AssessmentSummaryCard        (status, date, duration, overall/aptitude score)
       ├─ ProcessingStatusBadges       (Uploaded / Transcribed / Analyzed / Completed)
       ├─ CommunicationOverviewCard    (overall/reading/listening/confidence scores)
       ├─ StrengthsImprovements        (strengths_json / improvements_json badges)
       ├─ RecordingAnalysisCard × 2    (Read Aloud, Listen & Repeat — reference
       │                                sentence, transcript, type-specific metrics)
       ├─ AudioPlayerCard × 2          (native <audio controls>, blob-fetched)
       └─ AssessmentTimeline           (7-step derived progression)
```

Every section handles its own missing/pending/failed state inline (per-field
status checks + empty-state copy) rather than a single top-level error
boundary — mirrors the "one query/one section owns its own state" pattern
already used by `candidate-profile-view.tsx`'s tabs.

## 4. API usage (frontend)

- `frontend/src/services/assessment-dashboard.service.ts` — `getFull`,
  `getSessionByCandidate`, `downloadRecording` (blob fetch, since a plain
  `<audio src>` can't carry the bearer auth header — same pattern as
  `candidateService.downloadResume` / `resume-tab.tsx`).
- `frontend/src/hooks/use-assessment-dashboard.ts` — `useAssessmentSessionFull`
  (one query, React Query), `useAssessmentSessionByCandidate` (`retry: false`,
  since a 404 there is an expected "not started" state).
- Types hand-typed in `frontend/src/types/assessment-dashboard.types.ts` to
  mirror the new Pydantic schemas exactly, matching the project's existing
  no-codegen convention.

## 5. Future enhancements

- **Aptitude scoring**: the summary card currently shows a placeholder
  ("Aptitude scoring not yet available") since no aptitude-scoring pipeline
  exists yet — wire it in once that scoring engine ships.
- **Per-campaign reference sentences**: today's single global Read Aloud /
  Listen & Repeat sentence is a known MVP limitation (see `config.py`'s own
  docstring); once a content-management model exists, `AssessmentDashboardService.get_full`
  is the one place that needs to resolve a session-specific sentence instead.
- **Audio delivery**: recordings are streamed through the API and fetched as
  blobs client-side. If recordings move to S3/MinIO, a presigned URL would let
  `<audio>` fetch directly, removing the blob round-trip.
- **Recruiter-initiated invites**: there's currently no in-app flow to send a
  candidate their assessment link — the emailed link with `campaign_id`/`candidate_id`
  query params is generated out-of-band. A future sprint could add that flow
  and use `POST /assessment/session` (already idempotent) to send it.
