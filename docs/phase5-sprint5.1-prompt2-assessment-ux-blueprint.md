# TalentLens — Phase 5 (MVP)
# Sprint 5.1 — Prompt 2
## Assessment Flow & User Experience Design Blueprint

Status: Design only. No code, components, database models, or API implementations exist yet as a result of this document.
Relationship to Prompt 1: [phase5-sprint5.1-assessment-management-architecture.md](phase5-sprint5.1-assessment-management-architecture.md) designed the general-purpose Assessment Management *system* (templates, question bank, configurable lifecycle). **This document deliberately narrows that system's first release to one fixed, hardcoded assessment** — five Aptitude questions, one Read Aloud exercise, one Listen & Repeat exercise, in that fixed order, nothing configurable. Where the two documents seem to disagree (e.g. Prompt 1 designs a Template/Question-builder submodule; this MVP explicitly forbids building one yet), this document wins for what ships in Sprint 5.1 — Prompt 1's generality is the target the UX in this document must not architecturally block, not something to build now (see §10).

---

## 0. MVP Framing

The fixed content, in fixed order, no branching:

```
Section 1 — Aptitude              5 fixed multiple-choice/short-answer questions
Section 2 — Read Aloud            1 fixed sentence, candidate reads it, records once
Section 3 — Listen & Repeat       1 fixed sentence played by the system, candidate repeats, records once
                                   → Assessment ends
```

No template picker, no question authoring UI, no configurable time-per-section screen for the recruiter to build — those are Prompt 1's future surface. For this MVP, the recruiter's only real decision is *whether to send this one assessment to a candidate*, not what's in it.

Existing components confirmed available and reused throughout (no new design system, per the platform's standing convention): `card.tsx`, `button.tsx`, `dialog.tsx`, `progress.tsx`, `badge.tsx`, `sonner.tsx` (toasts), `tabs.tsx`, `skeleton.tsx`, `table-empty-state.tsx`. No audio-recording primitive exists yet in the frontend today — this is genuinely new interaction surface, designed fresh in §4/§5, built from the same visual language as everything else (no new component library).

---

## 1. Complete Candidate Journey

```
Recruiter sends invitation
        │
        ▼
Candidate receives email with invitation link
        │
        ▼
[Landing Screen]            token validated, assessment title + estimated duration shown
        │
        ▼
[Instructions Screen]        explains 3 sections, no going back once started, one attempt
        │
        ▼
[Permissions Screen]         microphone access requested (blocking — sections 2 & 3 need it)
        │
        ▼
[Section 1 — Aptitude]       5 questions, one at a time, forward/back within section allowed
        │
        ▼
[Section 1 Review]           summary of 5 answers, "Submit Section 1" (locks answers)
        │
        ▼
[Section 2 — Read Aloud]     sentence shown → record → preview → continue
        │
        ▼
[Section 3 — Listen & Repeat] sentence played once → record → continue
        │
        ▼
[Submitting] (brief processing state — uploading final recording, finalizing session)
        │
        ▼
[Completion Screen]          "You're done" — no score shown (manual recruiter review, per Prompt 1 §6)
```

Every transition is **one-directional once a section is submitted** — a candidate can move back and forth *within* Section 1 (it's the only section with multiple discrete questions to revisit), but cannot return to Section 1 once in Section 2, and cannot re-record Section 2 once Section 3 begins. This mirrors Prompt 1's "Published assessment questions are locked" principle, applied at the candidate-attempt level: once you move forward, the prior section's answer is final.

Every screen transition passes through the same session-state check (has this invitation already been used / expired / revoked?) so a candidate refreshing mid-assessment always resumes exactly where they left off (§7).

---

## 2. Assessment Screens

| Screen | Purpose | Key elements |
|---|---|---|
| **Landing** | First thing a candidate sees after clicking the invitation link | Assessment name, org/company name, total estimated time (~10–15 min for this fixed MVP), "Begin" button. If the token is invalid/expired/revoked, this screen renders the corresponding error state instead (see Error Screens below) — never a raw crash or blank page. |
| **Instructions** | Sets expectations before anything starts | Plain-language explainer of the 3 fixed sections in order, a call-out that the assessment cannot be paused/restarted once begun (one attempt, per Prompt 1's attempt-limit model), a "Continue" button. |
| **Permissions (Microphone)** | Requests mic access before Section 2 is reachable | Explains *why* (Sections 2 & 3 require voice recording), a native browser permission prompt is triggered on explicit user action (never auto-triggered on page load — browsers block/ignore that, and it also gives the candidate the instructional context first), with a fallback screen if denied (see Validation, §7). |
| **Assessment (Section 1 — Aptitude)** | The question-answering screens | See §3. |
| **Assessment (Section 2 — Read Aloud)** | The reading-recording screen | See §4. |
| **Assessment (Section 3 — Listen & Repeat)** | The listen-then-repeat screen | See §5. |
| **Progress** | Not a standalone screen — a persistent header/footer element present across all three sections | See §8. |
| **Completion** | Terminal success screen | Confirmation the assessment was received, no score/result shown (matches Prompt 1's manual-review lifecycle — nothing to show yet), optional "what happens next" copy, no further navigation (candidate has nowhere else to go in this flow, consistent with Prompt 1 §7's "no login, no dashboard" design for candidates). |
| **Error — Timeout** | Section or full-assessment time limit reached | Distinguishes "this section's time is up, moving on automatically" (soft, if per-section timing is used) from "your invitation link expired" (hard stop, links back to nothing — candidate must contact the recruiter). |
| **Error — Network Failure** | Connectivity lost mid-assessment (esp. mid-recording or mid-submit) | Non-destructive: never discards captured answers/recordings already held locally; shows a retry action; auto-retries the failed submit call a bounded number of times before surfacing the manual retry button. |

---

## 3. Section 1 — Aptitude (5 fixed questions)

**Layout**: one question per screen (not a single long-scroll form) — keeps focus, keeps progress legible, matches how Sections 2/3 are also single-focus-per-screen.

- **Question card**: question text, answer options (radio group, reusing `radio-group.tsx`) or short-answer input (`input.tsx`/`textarea.tsx` depending on question), rendered inside the existing `card.tsx`.
- **Navigation**: "Back" (enabled from Question 2 onward) and "Next" (disabled until the current question has an answer — this MVP requires every question answered, no skip, since there are only 5 and reordering/skip logic is exactly the kind of configurability this MVP intentionally avoids). "Next" on Question 5 leads to the Section 1 Review screen, not directly into Section 2.
- **Timer**: a single section-level timer (not per-question) — persistent, non-modal element in the header (see §8), counts down; reaching zero auto-advances to the Review screen with whatever is answered (unanswered questions marked as such, not blocking submission — a hard per-question requirement plus a hard countdown would let a slow connection or slow reader lock a candidate out entirely, which is too punishing for an aptitude check).
- **Question progress**: "Question 3 of 5" indicator + a 5-segment progress bar (reusing `progress.tsx`), always visible.
- **Answer review**: the Section 1 Review screen lists all 5 questions with the candidate's chosen/typed answer next to each, each with an "Edit" affordance that jumps back to that specific question (still within Section 1 — this is the one place backward navigation is unrestricted, since Section 1 hasn't been submitted yet).
- **Submission**: an explicit "Submit Section 1" button on the Review screen — this is the one section-boundary action that's a deliberate candidate decision (not an automatic "last answer = submitted"), because unlike Sections 2/3 (single recording, obviously final), a 5-question review benefits from an explicit checkpoint.

---

## 4. Section 2 — Read Aloud

Single fixed sentence, single recording attempt, linear interaction:

```
[Screen loads]
      │
      ▼
Sentence displayed (large, high-contrast text, always visible while recording)
      │
      ▼
"Start Recording" button (primary CTA, explicit user action — mic access already
 granted in the Permissions screen, so this only starts capture, no permission
 prompt at this point)
      │
      ▼
Recording indicator appears (visible "recording" state: pulsing dot + elapsed-time
 counter + waveform-style level meter so the candidate has live feedback that audio
 is actually being captured — silence with no visible feedback is the #1 cause of
 candidates re-attempting incorrectly)
      │
      ▼
"Stop Recording" button (explicit candidate action — this fixed MVP does not
 auto-stop on silence-detection; that's an enhancement, not a requirement for
 a single fixed sentence)
      │
      ▼
Preview screen: playback control (Play/Pause) over the just-recorded audio,
 plus two actions: "Re-record" (discards, returns to the pre-recording state
 with the sentence still shown) and "Continue" (locks the recording, advances
 to Section 3)
```

Design notes:
- The sentence stays on-screen through the entire recording, not just before it starts — candidates read while recording, they don't memorize first.
- "Re-record" is allowed **before** Continue is pressed (unlimited re-tries during the preview step), but once "Continue" is pressed the recording is final — no re-record after leaving the screen. This matches Prompt 1's "session progression is one-directional" principle applied at the exercise level.
- Empty/silent recordings are caught here, not later (see §7 Validation) — the Preview screen actively surfaces "we couldn't detect audio in this recording" rather than silently accepting a blank file, with "Re-record" as the immediate next action.

---

## 5. Section 3 — Listen & Repeat

Same recording mechanics as Section 2, different setup phase:

```
[Screen loads]
      │
      ▼
"Play Sentence" button (single fixed sentence, audio only — no text shown, since
 seeing the sentence would make this a reading exercise, not a listening one)
      │
      ▼
Sentence plays once, automatically disables further playback (button becomes
 disabled/labeled "Played" — this MVP allows exactly one listen, per the prompt's
 explicit "candidate can listen once" spec)
      │
      ▼
"Start Recording" button becomes enabled only after playback finishes
      │
      ▼
Recording indicator (identical component to Section 2 — same pulsing dot +
 elapsed-time + level meter, for interaction consistency across both audio
 exercises)
      │
      ▼
"Stop Recording" button
      │
      ▼
Preview screen (identical shape to Section 2's: Play/Pause, Re-record, Continue)
      │
      ▼
"Continue" → assessment complete, moves to Submitting/Processing → Completion Screen
```

Design notes:
- Because the candidate cannot re-hear the sentence, the pre-recording state should include a brief, low-pressure "take a moment, then start recording when ready" affordance rather than forcing immediate recording the instant playback ends — a rigid "recording starts automatically when audio stops" would punish normal human reaction time.
- Re-record is still allowed at the Preview step (same as Section 2) even though re-listening is not — those are two different affordances (fixing a bad *recording* vs. getting a second *listen*), and only the latter is restricted by the prompt's spec.

---

## 6. Recruiter Experience

Recruiter-facing status model, consistent with the four states named in the prompt:

| Status | Meaning | Recruiter-visible actions |
|---|---|---|
| **Not Started** | Invitation sent, candidate hasn't opened/started the assessment yet | Resend, Revoke (same actions Prompt 1 §14 already specifies for invitations generally) |
| **In Progress** | Candidate has started at least Section 1 but hasn't completed Section 3 | Read-only visibility into *which* section they're on (not answer content mid-attempt) — gives the recruiter a sense of whether a candidate stalled |
| **Completed** | All 3 sections submitted, recordings uploaded successfully | "Review" action becomes available |
| **Review Pending** | Completed, awaiting recruiter's manual review (per Prompt 1's no-auto-scoring MVP decision) | Opens the Review screen: Section 1 answers displayed plainly (question + candidate's answer, no automated correctness scoring in this MVP — the recruiter judges), Section 2 & 3 recordings playable inline, a single "Mark Reviewed" action once the recruiter is done (mirrors Prompt 1 §6's Submitted → Under Review → Completed lifecycle, applied to this MVP's fixed content) |

The recruiter's list/table view (reusing `data-table.tsx`) shows one row per invited candidate with their current status as a `badge.tsx`-styled pill — this is the same "progress table" concept as Prompt 1 §8/§15, just with a fixed, non-configurable status set instead of a general funnel.

---

## 7. Validation Rules

| Scenario | Handling |
|---|---|
| **Microphone permission not yet granted** | Permissions screen blocks progression into Section 2 with a clear explanation and a retry action; Section 1 (no audio needed) is reachable regardless, since gating the *entire* assessment on mic access the candidate hasn't been asked about yet would be premature. |
| **Microphone permission denied** | Dedicated error state (not a generic error) explaining that Sections 2 & 3 require microphone access, with instructions to re-enable it in browser settings and a "Try Again" action that re-triggers the permission prompt. The candidate is not silently stuck — this is a named, designed screen. |
| **No microphone hardware detected** | Distinct from "denied" — detected via the recording API failing to enumerate an audio input device; messaging is corrected accordingly ("we couldn't detect a microphone on this device") rather than reusing the "permission denied" copy, since the fix is different (use a different device vs. change a setting). |
| **Recording failure mid-capture** (device disconnected, browser crash-recovery, etc.) | Preview screen never shows a broken/empty player — if capture failed, the candidate lands back at the pre-recording state with a toast (`sonner.tsx`) explaining the recording didn't complete, not silently on the Preview screen with nothing to play. |
| **Empty/silent recording** | Detected at the Preview step (basic audio-level check on the captured file) — surfaced as a specific message ("we couldn't detect audio"), not treated as a valid completed recording; "Re-record" is the offered fix. |
| **Section time limit reached** | Auto-advances (Section 1) rather than hard-locking the candidate out — see §3. Sections 2/3 have no meaningful "time limit" beyond the recording itself being bounded by a sane max duration (e.g. capped recording length as a safety net, not a candidate-facing countdown, since both are single-sentence exercises). |
| **Browser refresh mid-assessment** | Session recovery (below) resumes exactly where the candidate left off — refresh must never restart the whole assessment or forfeit the attempt, since this MVP grants exactly one attempt (Prompt 1's attempt-limit model) and an accidental refresh shouldn't cost it. |
| **Session recovery** | On any screen load, the app first checks invitation/session status server-side (same `RequireInvitationToken`-scoped check from Prompt 1 §12) before rendering any assessment screen: if a section was already submitted, the candidate is placed at the next unsubmitted section, never back at a completed one; if a recording was already uploaded and locked, it is not re-recordable on resume. |
| **Network failure during submit** | Locally-held answer/recording data is not discarded on a failed submit call — the UI retries automatically a bounded number of times, then surfaces a manual "Retry" action (Error — Network Failure screen, §2) that resubmits the same already-captured data rather than asking the candidate to redo the section. |

---

## 8. Progress Tracking

Two levels, always visible, never requiring the candidate to guess where they are:

- **Overall progress**: a persistent 3-segment indicator (Aptitude / Read Aloud / Listen & Repeat) in a fixed header, present on every assessment screen — segments fill in as each section is submitted. This is the "how much of the whole thing is left" signal.
- **Section progress**: contextual to the current section —
  - Section 1: "Question 3 of 5" + 5-segment sub-bar (§3).
  - Section 2 / 3: a simpler binary state (not-yet-recorded → recording → recorded), since each is a single exercise, not a multi-item list — shown as a step indicator ("Read → Record → Review") rather than a percentage, which would be misleading for a 1-item section.
- **Completion percentage**: derived, not separately tracked — Section 1 contributes 5 discrete completion units, Sections 2 and 3 contribute 1 unit each (recording locked in) for a combined 7-unit total, giving a single overall percentage if a summary number is wanted anywhere (e.g. the recruiter's "In Progress" tooltip) without inventing a second progress model.

---

## 9. Accessibility

- **Keyboard navigation**: every control (Next/Back, Start/Stop Recording, Play Sentence, Submit, Continue, Re-record) must be reachable and operable via Tab/Enter/Space alone — no interaction in this flow (especially the recording controls) should require a mouse, since some candidates will be using assistive tech or simply prefer keyboard control under time pressure.
- **Color contrast**: recording/progress states (the pulsing "recording" indicator, progress segments, error banners) must not rely on color alone to convey meaning — pair color with icon/text (e.g. a mic icon + "Recording…" label, not just a red dot) so the flow remains legible under the platform's existing dark theme for users with color-vision deficiencies.
- **Screen readers**: dynamic state changes (recording started/stopped, section submitted, timer reaching a warning threshold) must be announced via ARIA live regions — a candidate using a screen reader has no other way to know a silent visual-only state (like "recording in progress") has changed.
- **Captions**: the Listen & Repeat sentence, while intentionally audio-only *during the exercise* (per its design intent — hearing it, not reading it, is the point), should have a text transcript available through an accessibility-specific affordance (not shown by default, since that would defeat the exercise) for candidates who are Deaf or hard-of-hearing — this needs a product decision on whether an alternate non-audio path is offered for this section entirely, flagged here as an open question rather than silently assumed.

---

## 10. Future Compatibility

This MVP's screens are built so that generalizing to Prompt 1's full configurable system is a **content and data-source change, not a screen redesign**:

- **Configurable assessments**: every screen in this document already treats its content as data (a question, a sentence, a section count) rather than hardcoding layout around "exactly these 5 questions" — Section 1's question-per-screen pattern already generalizes to N questions with no layout change; only the data source moves from a fixed constant to Prompt 1's `AssessmentQuestion` records.
- **More aptitude questions**: the Question progress indicator (`§8`, "Question X of N") and the 5-segment bar are already N-based in spirit; scaling from 5 to any N is a data change, not a redesign.
- **Multiple communication exercises**: Sections 2 and 3 are already modeled as instances of the same "audio exercise" interaction shape (sentence/prompt → record → preview → continue) with only the setup step differing (shown vs. played once). Adding a third or fourth communication exercise type reuses this same shape; a genuinely new exercise *type* (e.g. a video response) would extend the shape, not replace it.
- **Coding tests**: fits the same overall section-sequence model (a new section type between or alongside existing ones) — the Progress Tracking model (§8) already treats "a section" as a countable unit agnostic to its internal content, so a code-editor section slots in as one more segment.
- **AI interviews (Phase 6)**: per Prompt 1 §16, an interview is another session type reusing the same start/record/submit lifecycle this document already establishes for Sections 2/3 — the recording UI (indicator, preview, re-record-before-continue) is the direct ancestor of an interview-question recording screen, needing extension (e.g. multi-turn, AI-generated follow-ups) rather than replacement.

The single architectural discipline that makes this possible: **every screen in this MVP is a "renderer of section content + a fixed interaction shape," never a screen that assumes "there are exactly 3 sections" or "there are exactly 5 questions" in its own layout logic** — those numbers are MVP *content* decisions, not UI *structure* decisions. Prompt 1's Templates/Question Bank submodule, when built, becomes the content source these same screens read from.
