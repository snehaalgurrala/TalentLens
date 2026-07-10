# TalentLens — Phase 5, Sprint 5.7, Prompt 13B
# Recruiter Invitation UI + Candidate Assessment Entry

Connects the invitation backend from Prompt 13A to the UI on both ends:
recruiters can select candidates in a campaign and send them an assessment
invitation email; candidates who click the emailed link land straight in the
existing assessment runner with no manual setup. Two small backend additions
(`POST /assessment/invitations/{token}/start` and `.../complete`) were needed
to make the STARTED/COMPLETED lifecycle automatic — everything else reuses
13A's endpoints and this repo's existing table/dialog/toast/React Query
conventions.

```
Recruiter (Candidates list, one campaign selected)
    │  select rows → "Send Assessment" → expiration dialog → Confirm
    ▼
POST /assessment/invitations/send  →  toast + per-candidate success/failure list
                                              │
                                     (email, out of UI's control)
                                              ▼
Candidate clicks link → /assessment/start/{token}
    │  GET /assessment/invitations/{token}        (marks OPENED, server-side)
    ▼
stores session_id + token in AssessmentRunnerProvider
    ▼
router.replace("/assessment/device-check")  ── same runner as today ──►
    device-check → instructions ["Continue" → POST .../start, marks STARTED]
    → aptitude → read-aloud → listen-repeat → uploading
    [bothUploaded → POST .../complete, marks COMPLETED] → completed
```

## 1. Backend additions (small, needed for Part 4)

13A shipped `AssessmentInvitationRepository.mark_started`/`mark_completed`
but nothing called them — there was no candidate-reachable endpoint yet.
This sprint adds two, in `app/api/v1/endpoints/assessment_invitations.py`,
with the exact same public/token-secured access model as the existing
`GET /{token}`:

| Method | Path | Behavior |
|---|---|---|
| POST | `/assessment/invitations/{token}/start` | Marks STARTED. Idempotent (no-op if already STARTED). `410` if already COMPLETED/REVOKED/EXPIRED. |
| POST | `/assessment/invitations/{token}/complete` | Marks COMPLETED. Idempotent — an already-COMPLETED invitation is left as-is, not rejected, so a candidate's retry/double-submit never surfaces as an error. |

`AssessmentInvitationService` was refactored to share the token-lookup +
lazy-expiry + REVOKED/EXPIRED checks (`_get_live_invitation`) and the
session/campaign/candidate response assembly (`_build_detail_response`)
across `get_invitation_by_token`, `mark_started`, and `mark_completed` —
previously that logic only existed once, inline in
`get_invitation_by_token`.

Both endpoints, the service methods, and the idempotency/terminal-status
edge cases are covered in `tests/test_assessment_invitation_service.py`
(`TestMarkStarted`, `TestMarkCompleted`) and
`tests/test_assessment_invitations_api.py` (`TestStartInvitation`,
`TestCompleteInvitation`).

## 2. Recruiter workflow

`CandidatesBulkActionBar` (`frontend/src/features/candidates/`) gained two
new optional props, `campaignId` and `candidates` (the full
`CandidateListItem[]`, not just the selected id set it already received) —
needed because every other bulk action here operates on `resume_file_id`,
but sending an invitation needs `candidate_id` + `campaign_id`. Both list
views that already own this data pass it straight through
(`candidates-list-view.tsx`, `pipeline-board/pipeline-board-view.tsx`); the
"Send Assessment" button only renders when `campaignId` is present, so the
bar stays usable in any context that doesn't have one.

New `SendAssessmentDialog` (`send-assessment-dialog.tsx`) is a two-stage
dialog, reusing `Dialog`/`RadioGroup`/`Input`/`Button` exactly like the
existing Assign/Delete/Archive/Move dialogs in the same file:

1. **Form stage** — expiration presets (24h / 48h / 72h / Custom, via
   `RadioGroup`), a number input for Custom (clamped 1–2160 hours client-side
   to match the backend's bounds), and a Send button.
2. **Results stage** — after `POST /assessment/invitations/send` resolves,
   the same dialog switches to a success/failure summary plus a per-failed-
   candidate reason list (name resolved from the `candidates` prop), closing
   only when the recruiter clicks Done. A toast fires alongside (matching
   every other bulk action's `reportResult` pattern) for at-a-glance
   feedback; the in-dialog list is what satisfies "per-candidate errors."

## 3. Candidate workflow

New route `/assessment/start/[token]` (`app/(candidate-assessment)/assessment/start/[token]/page.tsx`,
async `params` per this repo's Next 15 convention — see
`assessment/aptitude/[questionId]/page.tsx`) renders
`InvitationEntryScreen`, which:

1. Calls `useInvitationByToken(token)` (`GET /assessment/invitations/{token}`
   — this call is what marks the invitation OPENED server-side; no separate
   frontend call needed).
2. On success, stores `assessment_session.id` and the raw `token` in
   `AssessmentRunnerProvider` (`setSessionId` / new `setInvitationToken`),
   then `router.replace("/assessment/device-check")` — "opens automatically,"
   no landing-page click required.
3. On error, distinguishes five states entirely from the backend's status
   code + `detail` text (no new backend fields needed): `404` → Invalid
   Link, `410` containing "revoked" → Revoked, "completed" → Already
   Completed, any other `410` → Expired, `status: 0` (no response) →
   network failure with a Retry button that calls `refetch()`.

Errors and the loading state reuse `AssessmentScreenShell` + `Card` — the
same shell `LandingScreen`'s "Invalid Assessment Link" card already used —
rather than a new page chrome.

## 4. Assessment Runner changes (Part 3)

`AssessmentRunnerProvider` gained one field, `invitationToken: string | null`
(reset to `null` in `resetAssessment()` alongside `sessionId`). Nothing else
in the runner changed: `sessionId` was already the only thing every
downstream screen (`device-check`, `instructions`, `aptitude/*`,
`read-aloud`, `listen-repeat`, `uploading`) depends on, so removing the
`campaign_id`/`candidate_id` dependency for the *primary* flow only required
adding the new token-based entry point above — `landing-screen.tsx` (the old
`/assessment?campaign_id=&candidate_id=` entry, which calls the
recruiter-authenticated `POST /assessment/session` directly) was left
untouched and still works, satisfying "maintain backward compatibility for
developer testing." `invitationToken` stays `null` on that path, so the
STARTED/COMPLETED calls below simply never fire for dev-testing sessions.

## 5. Automatic status updates (Part 4)

| Status | Trigger | Where |
|---|---|---|
| OPENED | Automatic, server-side, inside `GET /assessment/invitations/{token}` | `InvitationEntryScreen` (calls the GET as a side effect of rendering) |
| STARTED | Candidate clicks Continue on the instructions screen | `instructions-screen.tsx` → `useMarkInvitationStarted()` |
| COMPLETED | Both recordings finish uploading | `uploading-screen.tsx` → `useMarkInvitationCompleted()`, guarded by a ref so it fires exactly once |

Both STARTED/COMPLETED calls are best-effort and fire only when
`invitationToken` is set: they're a side-signal for the recruiter dashboard,
not a gate on the candidate's own progress, so a network failure there must
never block navigation into or through the assessment. Neither call has an
`onError` handler for this reason — a lost status update is acceptable; a
candidate stuck mid-assessment because of it is not.

## 6. Frontend files

New: `types/assessment-invitation.types.ts`,
`services/assessment-invitation.service.ts`,
`hooks/use-assessment-invitations.ts`,
`features/candidate-runner/invitation-entry-screen.tsx`,
`features/candidates/send-assessment-dialog.tsx`,
`app/(candidate-assessment)/assessment/start/[token]/page.tsx`.

Modified: `assessment-runner-context.tsx` (invitationToken),
`instructions-screen.tsx` / `uploading-screen.tsx` (status triggers),
`candidates-bulk-action-bar.tsx` / `candidates-list-view.tsx` /
`pipeline-board-view.tsx` (Send Assessment wiring).

## 7. Tests

- Backend: see §1 above (13 new service/API test cases).
- `instructions-screen.test.tsx` (new) — Continue navigates correctly with
  and without an invitation token; STARTED is only reported when a token is
  present.
- `uploading-screen.test.tsx` (extended) — COMPLETED is reported once, only
  when a token is present, without affecting the existing upload/retry/
  navigation assertions.
- `invitation-entry-screen.test.tsx` (new) — loading state, success →
  context + navigation, and all five error views (invalid/expired/revoked/
  completed/network-with-retry).
- `send-assessment-dialog.test.tsx` (new) — default/preset/custom expiration
  values sent to the API, disabled-Send on invalid custom input, and the
  success/failure breakdown view.
- `candidates-list-view.test.tsx` (extended) — end-to-end through the real
  bar + dialog (service layer mocked, not the hooks) confirming the button
  only appears with a campaign selected, the right `campaign_id`/
  `candidate_id`s are sent, and Done clears the selection.

## 8. Quality

`npx tsc --noEmit`, `npx eslint .`, and `npx jest` (107 tests, 33 suites) all
pass with no regressions; `npm run build` (Turbopack) succeeds and lists
`/assessment/start/[token]` as a dynamic route. Backend: `ruff check` clean,
888 backend unit tests pass (`pytest tests/ --ignore=tests/integration`).
