# candidate-runner

Candidate-facing assessment flow (Sprint 5.1 Prompt 3/4, Sprint 5.2 Prompt 6). Originally built as
a **mock-data-only** prototype with no backend, API calls, database, or authentication — swappable
for real data sources without a screen redesign, per
`docs/phase5-sprint5.1-prompt2-assessment-ux-blueprint.md` §10.

As of Prompt 4, Section 2 (Read Aloud) and Section 3 (Listen & Repeat) use **real browser
microphone recording** via the MediaRecorder API. As of Prompt 6
(`docs/phase5-sprint5.2-prompt6-assessment-recording-upload.md`), those recordings are **really
uploaded** to the backend and persisted via `StorageBackend` — the landing screen creates/resumes a
real `session_id` from `campaign_id`/`candidate_id` query params, and the uploading screen performs
real per-recording uploads with progress and retry. Aptitude, device check, and completion remain
simulated.

## Routes

Pages live in a dedicated, chrome-less route group so the candidate flow never renders the
recruiter dashboard's sidebar/nav:

```
src/app/(candidate-assessment)/
  layout.tsx                      mounts AssessmentRunnerProvider for the whole flow
  assessment/
    page.tsx                      Landing
    device-check/page.tsx         Device Check
    instructions/page.tsx         Instructions
    aptitude/
      [questionId]/page.tsx       Question screen (questionId 1-5)
      review/page.tsx             Review Answers
    read-aloud/page.tsx           Section 2 — Read Aloud
    listen-repeat/page.tsx        Section 3 — Listen & Repeat
    uploading/page.tsx            Submitting / processing animation
    completed/page.tsx            Completion screen
```

Every `page.tsx` is a thin wrapper that sets `metadata` and renders one screen component from this
folder — no logic lives in `src/app`.

## Folder contents

```
types.ts                          Shared types (AptitudeQuestion, DeviceCheckState, ...)
mock-data.ts                      Hardcoded questions, sentences, assessment metadata
assessment-runner-context.tsx     Scoped Context provider + hook for flow state
assessment-screen-shell.tsx       Centered/branded shell for non-section screens
assessment-progress-header.tsx    Persistent 3-segment section progress header
timer.tsx                         Visual-only countdown (Section 1)
use-audio-recorder.ts             MediaRecorder-backed recording hook (permission, capture, errors)
recording-card.tsx                Reusable record/preview/re-record/delete control (real audio)
landing-screen.tsx                Screen components (one per screen listed above)
device-check-screen.tsx
instructions-screen.tsx
aptitude-question-screen.tsx
aptitude-review-screen.tsx
read-aloud-screen.tsx
listen-repeat-screen.tsx
uploading-screen.tsx
completion-screen.tsx
index.ts                          Barrel export
```

## State management

`AssessmentRunnerProvider` (mounted once in the route group's `layout.tsx`) holds all cross-screen
state for the flow — device check results, aptitude answers, section-submission flags, and the
Section 1 timer deadline — via React Context, mirroring the existing `src/store/*-store.tsx`
Provider+hook pattern. It is intentionally **not** added to the global `AppProviders` tree: it is
scoped to this route group only, since candidate-runner state must never leak into the
authenticated app's state.

The captured recording itself (`RecordingAnswer`: `Blob` + object URL + duration + MIME type) is
lifted out of `RecordingCard` and held in `AssessmentRunnerProvider` as `readAloudRecording` /
`listenRepeatRecording`, mirroring the `answers` map used for aptitude. `RecordingCard` is
controlled via a `value`/`onChange` pair: it seeds `useAudioRecorder` from `value` on mount and
calls `onChange` on every capture/re-record/delete. Because client-side navigation inside the
`(candidate-assessment)` route group doesn't unload the page, the underlying `Blob`/object URL
stays alive in context, so a recording made in Read Aloud is still there (and still playable) if
the candidate navigates away and back. `resetAssessment()` revokes both object URLs before clearing
state to avoid leaking memory.

Per-recording *UI* state that doesn't need to survive navigation (waveform animation, playback
scrubber position) stays local to `RecordingCard`.

## Real audio recording

- `use-audio-recorder.ts` wraps `navigator.mediaDevices.getUserMedia` + `MediaRecorder`. States:
  `idle → requesting-permission → recording → recorded`, plus `unsupported` (feature-detected after
  mount, so SSR/CSR first render matches) and `error` (permission denied, no microphone, device
  disconnected mid-recording, or an unknown `getUserMedia`/`MediaRecorder` failure) — each with a
  user-friendly message.
- Preferred MIME type is `audio/webm;codecs=opus`, with `audio/webm` / `audio/ogg;codecs=opus` /
  `audio/mp4` fallbacks picked via `MediaRecorder.isTypeSupported` (see `src/utils/audio.ts`);
  `RecordingCard` renders the unsupported-browser message if none of these — and `MediaRecorder`
  itself — are available.
- Recording is capped at 60 seconds (`MAX_DURATION_SECONDS`) and auto-stops at the limit. Deleting
  or re-recording revokes the previous object URL. Microphone tracks are stopped as soon as
  recording stops (or the component unmounts) so the browser's mic-in-use indicator clears.
- Playback uses a real (visually hidden) `<audio>` element bound to the recording's object URL.

## Other mocking notes

- The uploading screen performs two real uploads (Read Aloud, Listen & Repeat) via
  `useUploadRecording` (`@/hooks/use-assessment-session`), each with real progress and a Retry
  button on failure, and auto-navigates to Completion once both report `UPLOADED`.
- Device Check auto-passes "Browser Supported" and "Internet Available" shortly after mount, and
  requires an explicit click for "Speaker Test" / "Microphone Ready" — all four are simulated (this
  screen does not yet use `use-audio-recorder.ts`).

## Known gaps vs. the full blueprint

This flow intentionally builds a smaller surface than
`docs/phase5-sprint5.1-prompt2-assessment-ux-blueprint.md` describes long-term — no dedicated
Permissions screen (folded into Device Check), no error/timeout/network-failure screens beyond the
recorder's own error state, and no accessibility captions affordance for Listen & Repeat. Audio
upload is now real (Prompt 6), but session resume is still recruiter-authenticated rather than a
real candidate token — there is no `AssessmentInvitation`/token-based, fully unauthenticated
candidate flow yet, and no Whisper/transcript/AI-scoring integration. These remain out of scope and
are backend/API-dependent follow-ups.
