# TalentLens — Phase 5, Sprint 5.1
# Assessment Management — Architecture Blueprint

Status: Design only. No code, SQL, models, or API implementations exist yet as a result of this document.
Audience: Engineering team implementing Sprint 5.1.
Constraint: Extends the existing platform. Does not alter Router → Service → Repository → Database, does not replace any technology, does not rename existing conventions.

---

## 0. Grounding: Conventions This Document Follows

Every recommendation below reuses patterns already live in the codebase (verified against the `campaigns` module, the current `UserRole` model, `celery_app.py`, `StorageBackend`, and the frontend `features/` layout) rather than introducing new ones:

- **Backend file naming**: bare domain noun per file (`campaign.py`), the layer lives in the folder, the suffix lives in the class name (`CampaignRepository`, `CampaignService`). Assessment Management follows this exactly — no `_service.py` / `_repository.py` suffixes.
- **RBAC**: `UserRole` enum (`SUPER_ADMIN`, `ORG_ADMIN`, `RECRUITER`, `CANDIDATE`) enforced via the `RequireRoles(*roles)` dependency and `CurrentUser` in `api/deps.py`. No decorators, no middleware-based auth.
- **Multi-tenancy**: explicit `org_id` column on every tenant-owned table, filtered per-query inside the repository layer (never a global session filter). Soft delete via `is_deleted`.
- **Workers**: Celery, event-triggered via `.delay(...)` from services, JSON serialization, `task_acks_late=True`. No scheduled/beat jobs exist yet — Sprint 5.1 introduces the platform's first one.
- **Storage**: `StorageBackend` ABC (`save`/`delete`/`load`), swappable via `storage/factory.py`, injected as a FastAPI dependency.
- **Frontend**: App Router route groups, `features/<domain>/` for UI, `services/<domain>.service.ts` wrapping the shared `apiClient` (axios), `hooks/use-<domain>.ts` with a query-key factory object, `types/<domain>.types.ts`, Zustand-style stores in `store/`.
- **Notable existing scaffolding**: the frontend already contains unimplemented placeholders — `assessment.service.ts`, `assessment.types.ts`, `notification.service.ts`, `notification.types.ts`, `notification-store.tsx`, `use-notifications.ts`. Sprint 5.1 is, in part, building the backend these stubs are waiting for.
- **Correction to the design-system assumption**: the current `components/ui/` + `design-system/tokens/` system is a clean dark-theme shadcn-style kit, but it does **not** currently implement glassmorphism (no blur/translucency tokens exist). Section 15 treats this honestly: reuse existing tokens as-is, and if glassmorphism is wanted, add it as new elevation/blur tokens through the existing token system rather than one-off CSS — this is *not* a redesign, it's a gap-fill.

---

## 1. Overall System Architecture

Assessment Management is a new **peer domain** alongside Campaigns, Candidates, and Recruiter Workflow. It does not sit "inside" any of them — it consumes Candidate identities and Organization/RBAC context that already exist, and it will itself be consumed by Phase 6 (AI Interview Agent).

```
                        ┌────────────────────────────┐
                        │        Frontend (Next.js)    │
                        │  (dashboard)  (candidate-run) │
                        └───────────────┬────────────┘
                                        │ REST (JSON)
                        ┌───────────────▼────────────┐
                        │           API Layer          │
                        │  /api/v1/assessments/*        │
                        │  /api/v1/assessment-templates │
                        │  /api/v1/public/assessments/*│  ← unauthenticated, token-scoped
                        │  /api/v1/notifications       │
                        └───────────────┬────────────┘
                                        │
                        ┌───────────────▼────────────┐
                        │         Router Layer          │
                        │  validation + RequireRoles /  │
                        │  RequireInvitationToken       │
                        └───────────────┬────────────┘
                                        │
                        ┌───────────────▼────────────┐
                        │        Service Layer          │
                        │  AssessmentService             │
                        │  AssessmentTemplateService      │
                        │  AssessmentInvitationService    │
                        │  CandidateSessionService        │
                        │  NotificationService (new)      │
                        └───────────────┬────────────┘
                                        │
                        ┌───────────────▼────────────┐
                        │       Repository Layer        │
                        │  org_id-scoped queries only    │
                        └───────────────┬────────────┘
                                        │
                        ┌───────────────▼────────────┐
                        │   PostgreSQL (+ pgvector)     │
                        └────────────────────────────┘

        Side channels (fired from Service layer, same as today):
        Service → Celery task (.delay) → Redis broker → Worker → DB / Email
        Service → StorageBackend (future: candidate-uploaded artifacts, e.g. code answers, recordings)
```

Two distinct traffic shapes hit this module:

1. **Recruiter-side** (authenticated, RBAC-gated, org-scoped) — identical shape to Campaigns today.
2. **Candidate-side** (unauthenticated or lightly-authenticated, token-scoped, single-tenant-by-token) — a new shape for the platform, isolated behind its own router prefix (`/api/v1/public/assessments/{token}`) and its own frontend route group, so it never shares middleware or layout with the recruiter dashboard.

Both shapes converge on the same Service and Repository layers — there is one `CandidateAssessmentSession` truth, viewed from two different entry points.

---

## 2. Module Responsibilities

| Submodule | Responsibility |
|---|---|
| **Assessment** | The recruiter-authored instance to be taken — metadata (title, description), configuration (time limit, attempt limit), lifecycle state, and the org that owns it. Composed of Questions (directly, or via a Template). |
| **Templates** | Reusable, versionable blueprints of question sets. Org-scoped by default; a `SUPER_ADMIN`-owned "platform library" flag allows shared templates across orgs (mirrors how nothing today is cross-org, so this is the one deliberate exception, gated by role). Instantiating an Assessment from a Template copies/snapshots questions so later template edits don't retroactively change assessments already sent. |
| **Questions** | Individual assessment items: prompt, type (multiple-choice, free-text, scenario/written — kept generic so Phase 6 can later add "verbal response" without a new submodule), scoring rubric metadata, ordering. Owned by a Template or directly by an Assessment. |
| **Invitations** | The bridge between an Assessment and a Candidate: generates a signed, single-use, expiring access token; tracks send/open/expire state independent of the session itself (an invitation can expire before a candidate ever starts). |
| **Candidate Sessions** | One attempt at an Assessment by a Candidate. Bounded by the Assessment's attempt limit. Owns timing (started_at, time remaining), status, and the collection of answers. This is the entity Phase 6 will extend. |
| **Progress Tracking** | Read-side aggregation over Candidate Sessions for the recruiter dashboard: per-question completion, time spent, last-activity heartbeat (for autosave/resume), and org-wide funnel stats (invited → started → completed). Deliberately modeled as a read path over Sessions, not a separate write-owning entity. |
| **Permissions** | Extension of the existing `UserRole` + `RequireRoles` model, plus one new primitive: `RequireInvitationToken`, the candidate-side equivalent of `CurrentUser` — resolves a signed token to a scoped session context instead of a JWT user. |
| **Notifications** | Event-driven messages triggered by lifecycle transitions (invitation sent, reminder, candidate completed, recruiter review needed). First real backend implementation of the domain the frontend already stubbed out. |
| **Future AI Integration** | Not built in Sprint 5.1. The module is shaped so that `AssessmentScoringService` (a placeholder service, see §3) and the existing embedding worker pattern become the seam Phase 6 plugs into — see §16. |

---

## 3. Backend Architecture

### Folder structure (extends existing layers, no new ones)

```
backend/app/
├── models/
│   ├── assessment.py                  # Assessment
│   ├── assessment_template.py         # AssessmentTemplate
│   ├── assessment_question.py         # AssessmentQuestion
│   ├── assessment_invitation.py       # AssessmentInvitation
│   ├── candidate_assessment_session.py# CandidateAssessmentSession
│   ├── candidate_answer.py            # CandidateAnswer
│   └── notification.py                # AppNotification (backs existing FE stub)
│
├── repositories/
│   ├── assessment.py                  # AssessmentRepository
│   ├── assessment_template.py         # AssessmentTemplateRepository
│   ├── assessment_question.py         # AssessmentQuestionRepository
│   ├── assessment_invitation.py       # AssessmentInvitationRepository
│   ├── candidate_session.py           # CandidateSessionRepository
│   └── notification.py                # NotificationRepository
│
├── services/
│   ├── assessment.py                  # AssessmentService — lifecycle, CRUD, publish/archive
│   ├── assessment_template.py         # AssessmentTemplateService
│   ├── assessment_invitation.py       # AssessmentInvitationService — token issuance/validation
│   ├── candidate_session.py           # CandidateSessionService — start/answer/submit/resume
│   ├── assessment_progress.py         # AssessmentProgressService — recruiter dashboard aggregates
│   ├── assessment_scoring.py          # placeholder seam for Phase 6 (no-op / manual review only in 5.1)
│   └── notification.py                # NotificationService — channel-agnostic dispatch
│
├── schemas/
│   ├── assessment.py
│   ├── assessment_template.py
│   ├── assessment_question.py
│   ├── assessment_invitation.py
│   ├── candidate_session.py
│   └── notification.py
│
├── api/v1/endpoints/
│   ├── assessments.py                 # recruiter-facing, RequireRoles-gated
│   ├── assessment_templates.py
│   ├── assessment_invitations.py
│   ├── public_assessments.py          # candidate-facing, RequireInvitationToken-gated
│   └── notifications.py
│
├── api/deps.py                        # + RequireInvitationToken (new, mirrors RequireRoles/CurrentUser)
│
├── workers/
│   ├── assessment_invitation_worker.py# send_invitation_email, send_reminder_email
│   ├── assessment_expiry_worker.py    # sweep job: expire overdue invitations/sessions
│   └── notification_worker.py        # dispatch_notification (channel fan-out)
│
├── notifications/                     # new: mirrors storage/ abstraction pattern
│   ├── base.py                        # NotificationChannel ABC: send(notification) -> None
│   ├── email.py                       # EmailChannel
│   └── factory.py                     # get_channels() -> list[NotificationChannel]
│
└── utils/
    └── tokens.py                      # signed invitation-token issuance/verification helpers
```

### Component interaction (unchanged flow, new participants)

- **Routers** validate input via Pydantic schemas and resolve identity via `CurrentUser` + `RequireRoles` (recruiter side) or `RequireInvitationToken` (candidate side). They never touch a repository directly.
- **Services** hold all business rules: lifecycle transition legality (§6), attempt-limit enforcement, token issuance delegation, triggering Celery tasks, and calling `NotificationService`. `AssessmentInvitationService` is the only service allowed to mint tokens (via `utils/tokens.py`), keeping token logic in one place.
- **Repositories** remain pure data access, every method taking `org_id` explicitly, exactly like `CampaignRepository.get_by_id(id, org_id)`.
- **NotificationService** is deliberately built like `StorageBackend`: an abstract `NotificationChannel` with a `send()` method, a `factory.py` selecting active channels from config. Today only `EmailChannel` exists; SMS/Teams/Slack (§11) are added later by dropping in a new channel class — zero changes to `AssessmentService` or any caller.
- **`assessment_scoring.py`** exists in 5.1 purely as an empty seam (manual recruiter review only, no auto-scoring) so Phase 6 has a pre-agreed file/class to extend rather than needing to introduce a new service later (see §16).

---

## 4. Frontend Architecture

### Pages (App Router, mirrors `features/campaigns` placement)

```
app/(dashboard)/assessments/                 # recruiter list view
app/(dashboard)/assessments/new/              # builder wizard
app/(dashboard)/assessments/[id]/             # detail: config + progress + review tabs
app/(dashboard)/assessment-templates/         # template library
app/(dashboard)/assessment-templates/[id]/    # template editor

app/(candidate-assessment)/[token]/           # NEW route group — no dashboard chrome,
                                               # unauthenticated layout, single purpose:
                                               # instructions → runner → submitted
```

The candidate route group is deliberately separate from `(dashboard)` — different layout (no sidebar/nav), different auth guard (`RequireInvitationToken`-backed client check, not the existing session/JWT guard), so a leaked link can never expose recruiter navigation.

### Feature modules (`features/assessments/`)

- `assessment-list-table.tsx`, `assessment-card.tsx` — mirrors `campaigns-table.tsx` / `campaign-card.tsx`.
- `assessment-builder-form.tsx` — multi-step form (React Hook Form + Zod), steps: details → questions → limits/config → review.
- `question-editor.tsx`, `question-list.tsx` — add/reorder/edit questions, drag-reorder consistent with existing table patterns.
- `invitation-dialog.tsx` — candidate selection (from an existing Campaign's candidate pool, or manual email entry) + send.
- `assessment-progress-table.tsx` — recruiter monitoring view (invited/started/completed/expired funnel), reuses `data-table.tsx` and `statistic-card.tsx`.
- `candidate-runner/` (separate feature folder, used only inside the `(candidate-assessment)` route group): `instructions-screen.tsx`, `question-navigator.tsx`, `timer-banner.tsx`, `answer-autosave-field.tsx`, `submission-confirmation.tsx`.

### Hooks (`hooks/use-assessments.ts`, `use-assessment-templates.ts`, `use-candidate-session.ts`)

Same query-key-factory shape as `use-campaigns.ts`:
```
assessmentKeys.all / .list(orgId) / .detail(id) / .progress(id) / .templates.list()
```
`use-candidate-session.ts` is the one hook that talks to the public/token-scoped API instead of the authenticated one — it takes the invitation token (from the route param) rather than relying on the global auth context, and includes autosave debounce logic (mutation fired on interval + on blur).

### API layer

- `services/assessment.service.ts`, `assessment-template.service.ts`, `assessment-invitation.service.ts` — thin wrappers over the existing shared `apiClient` (authenticated axios instance), exactly like `campaign.service.ts`.
- `services/candidate-session.service.ts` — wraps a **second**, unauthenticated axios instance (no interceptor attaching a JWT, since the candidate isn't logged in as a platform user) that instead attaches the invitation token as a path/query param. This reuses `services/axios.ts`'s factory pattern but configures a distinct client — it does not repurpose the interceptor-bearing `apiClient` used everywhere else, avoiding any risk of leaking a recruiter's session token into a candidate-facing tab.
- `services/notification.service.ts` — already stubbed; Sprint 5.1 wires it to the new `/api/v1/notifications` endpoints, no shape change needed if the stub's contract is respected.

### State management

- Server state: TanStack Query exclusively (existing convention) — no assessment data duplicated into Zustand.
- Client/UI state: local component state for builder wizard step, Zustand `notification-store.tsx` (already present) for the in-app notification bell/badge, following its existing shape.
- Candidate runner state (current question index, autosave status, time remaining) lives in a scoped local store/context inside the `candidate-runner` feature, not the global app store — it must not leak into or depend on the authenticated app's state tree.

### Navigation

- Recruiter side: new top-level nav item "Assessments" alongside Campaigns/Candidates in the existing dashboard sidebar, standard route-based active-state handling.
- Candidate side: no navigation chrome at all — a single linear flow driven by the invitation link, consistent with how one-shot external-facing flows should behave (nothing to navigate to; nothing to leak).

---

## 5. Database Planning (entities only — no tables, no columns beyond what's needed to explain relationships/ownership)

| Entity | Responsibility | Owned by (tenant) | Key relationships |
|---|---|---|---|
| `Assessment` | A recruiter-authored, sendable assessment instance | `org_id` (root of tenancy for this module) | belongs to Organization; created_by → User (recruiter); optionally instantiated_from → AssessmentTemplate; has many AssessmentQuestion |
| `AssessmentTemplate` | Reusable question-set blueprint | `org_id`, nullable for platform-library templates (owned instead by a `SUPER_ADMIN`/platform flag) | has many AssessmentQuestion (template-owned copies); referenced by Assessment at creation time (snapshot, not live link) |
| `AssessmentQuestion` | Single question | inherited via parent (Assessment or Template) — no independent org_id | belongs to exactly one Assessment OR one Template, never both |
| `AssessmentInvitation` | One candidate's invite to one Assessment | inherited via Assessment.org_id | belongs to Assessment; belongs to Candidate (existing entity); has a signed token, expiry, status |
| `CandidateAssessmentSession` | One attempt | inherited via Invitation → Assessment.org_id | belongs to AssessmentInvitation; bounded by Assessment.attempt_limit; has many CandidateAnswer |
| `CandidateAnswer` | One answer to one question in one session | inherited via Session | belongs to CandidateAssessmentSession; references AssessmentQuestion |
| `AssessmentAuditLog` | Security/compliance trail (token issued, token used, session accessed, tampering attempt) | inherited via Assessment.org_id | references Invitation/Session by id, immutable, append-only |
| `AppNotification` | In-app notification record | `org_id` + recipient User | references source event (invitation sent, session completed, etc.) polymorphically by type+id |

**Multi-tenancy strategy**: unchanged from the rest of the platform — explicit `org_id`-filtered repository queries, no ORM-level global filter, no separate schema-per-tenant. The one new wrinkle is the candidate-facing path, which authenticates by *token* rather than JWT; the repository layer still receives an explicit `org_id` for every query, it's just sourced from the validated token's embedded claim (set at invitation-issue time) instead of `CurrentUser.org_id`. This keeps the "every query is explicitly org-scoped" invariant intact even though the caller isn't a logged-in org member — see §12 for how the token carries that claim safely.

**Ownership summary**: Organization owns Assessments and Templates → Assessments own Questions and Invitations → Invitations own Sessions → Sessions own Answers. A strict tree, no cross-links except Invitation → Candidate (existing entity, cross-referenced not owned) and Assessment → Template (referenced at creation, then decoupled).

---

## 6. Assessment Lifecycle

```
Draft ──────► In Review ──────► Published ──────► Invitations Sent
  │                                                       │
  │ (recruiter can edit                                   ▼
  │  freely; not visible                          Candidate Started
  │  to any candidate)                                     │
  │                                                        ▼
  │                                                  In Progress
  │                                                        │
  │                                                        ▼
  │                                                   Submitted
  │                                                        │
  │                                                        ▼
  │                                              Under Review (recruiter)
  │                                                        │
  │                                                        ▼
  └───────────────────────────────────────────────►  Completed ──────► Archived

Side transitions (from any "sent/started/in-progress" state):
  Invitations Sent / Candidate Started ──(deadline passes)──► Expired
  Published / Invitations Sent ──(recruiter action)──► Revoked
```

- **Draft → In Review**: recruiter marks ready; triggers validation (at least one question, limits configured) but no external visibility change.
- **In Review → Published**: `ORG_ADMIN`/`RECRUITER` approval gate; the Assessment becomes eligible to receive invitations. Questions become **locked** at this point (edits after publish create a new version rather than mutating a live assessment candidates may already be mid-attempt on — protects data integrity of in-flight sessions).
- **Published → Invitations Sent**: fan-out of one `AssessmentInvitation` per selected candidate; each invitation independently tracks its own sub-state, so this is really "at least one invitation exists," not a single flag on the Assessment.
- **Invitation Sent → Candidate Started**: transition happens at the *Invitation/Session* level the moment `CandidateSessionService.start()` succeeds (token validated, attempt count checked); the Assessment's aggregate status (for dashboard purposes) reflects the furthest-progressed session.
- **In Progress → Submitted**: candidate hits submit, or the time limit auto-submits via the expiry worker's sweep — both paths converge on the same service method, `submit()` is idempotent per session.
- **Submitted → Under Review → Completed**: manual recruiter review (5.1) — no auto-scoring yet (`assessment_scoring.py` is a no-op placeholder). Completed is a per-session state; the parent Assessment moves to "Completed" for dashboard/reporting once recruiter marks the review done, or the Assessment itself is archived independent of stragglers.
- **Expired**: applies to an Invitation/Session whose deadline passed without submission — automatic, driven by `assessment_expiry_worker.py`'s scheduled sweep (§10), never a manual state.
- **Revoked**: recruiter-initiated cancellation of an invitation before completion (e.g., role filled) — invalidates the token immediately, distinct from Expired for audit clarity ("we pulled it" vs. "they ran out of time").
- **Archived**: terminal, read-only state for an Assessment as a whole; does not delete data (soft-delete convention, `is_deleted`/`is_archived` flag consistent with Campaign's soft-delete pattern), just removes it from active recruiter views.

---

## 7. Candidate Journey

```
Email/Invitation Link
        │
        ▼
Landing / Instructions Screen   ← token validated here (RequireInvitationToken);
        │                          shows assessment title, time limit, attempt count remaining
        ▼
Identity Confirmation           ← lightweight: confirm name/email tied to the invitation;
        │                          no password, no account creation required
        ▼
Assessment Runner                ← question navigator + timer banner; per-question
        │                          autosave (debounced) via candidate-session.service.ts
        ▼
Submission Confirmation          ← explicit "Submit" action or auto-submit at time limit
        │
        ▼
Processing (brief)               ← session finalized server-side (idempotent submit())
        │
        ▼
Completed / Thank-You Screen     ← no score shown in 5.1 (manual review only);
                                    optionally a "we'll follow up" message
```

Screen notes:
- **Landing/Instructions**: also where an expired, revoked, or already-exhausted (attempt-limit hit) token shows a clear, non-generic error state rather than a raw 401 — handled by `RequireInvitationToken` returning a typed status the frontend maps to a specific message.
- **Runner**: must tolerate refresh/tab-close mid-attempt — autosave + a `resume` capability (re-validating the same token returns the in-progress session rather than starting a new attempt) is a hard requirement, not a nice-to-have, since candidates are on uncontrolled devices/networks.
- **No login required** for external candidates: this is a deliberate deviation from the authenticated-everywhere pattern elsewhere in the platform, scoped tightly to this one flow and enforced entirely by the token, never by relaxing `CurrentUser`/`RequireRoles` elsewhere.

---

## 8. Recruiter Journey

```
Creating          → Assessment Builder: pick blank or Template, add questions, set limits
Publishing        → Review step surfaces validation errors; Publish locks question set
Inviting          → Select candidates (from a Campaign's pipeline, or ad-hoc by email) → send
Monitoring        → Progress table: Invited / Started / In-Progress / Submitted / Expired counts,
                     per-candidate drill-down, resend/revoke actions
Reviewing         → Open a Submitted session, view answers, mark Completed (manual, 5.1)
Archiving         → Archive the whole Assessment once recruiting need is over
```

The "Inviting" step is the one place this module touches an existing one directly: candidate selection should be able to pull from an existing Campaign's candidate list (reusing the already-parsed/ranked Candidate entities) rather than requiring recruiters to re-enter candidate emails — a read-only cross-reference, not a new coupling in the write path.

---

## 9. Permission Model

Extends `UserRole` — no new roles added, only new permission checks against the existing four:

| Action | `SUPER_ADMIN` | `ORG_ADMIN` | `RECRUITER` | `CANDIDATE` |
|---|---|---|---|---|
| Manage platform-library templates | ✅ | ❌ | ❌ | ❌ |
| Create/edit org templates | ✅ | ✅ | ✅ | ❌ |
| Create/edit/publish assessments | ✅ | ✅ | ✅ | ❌ |
| Send/revoke/resend invitations | ✅ | ✅ | ✅ | ❌ |
| View org-wide progress dashboard | ✅ | ✅ | ✅ (own assessments, same scoping as Campaigns today) | ❌ |
| Review submissions | ✅ | ✅ | ✅ | ❌ |
| Archive assessments | ✅ | ✅ | ✅ | ❌ |
| Access own assessment session | n/a | n/a | n/a | ✅ (token-scoped, not role-based) |
| List/view other candidates' sessions | ❌ (cross-org) | ❌ (own org only) | ❌ | ❌ |

Candidate access is **not** modeled as a permission grant on `UserRole.CANDIDATE` at all — it's a separate authorization primitive (`RequireInvitationToken`) because the actor may not even have a platform account. This keeps the existing `RequireRoles` semantics ("you are an authenticated member of this org with this role") clean and avoids overloading it with "you possess this one specific link."

---

## 10. Worker Integration

Existing pattern (event-triggered `.delay()` from services) covers most of this module directly:

| Task | Trigger | Queue |
|---|---|---|
| `send_invitation_email` | `AssessmentInvitationService.create()` after DB commit | `notifications` (new queue, separate from `resumes`/`embeddings` to avoid contention with the parsing pipeline) |
| `send_reminder_email` | scheduled (see below), or manual "resend" action | `notifications` |
| `dispatch_notification` | any lifecycle event needing an in-app/email notice | `notifications` |
| `generate_answer_embedding` (Phase 6 seam, not built in 5.1) | future: on submit, for semantic scoring | `embeddings` (existing queue, reused) |

**New capability required**: this is the platform's first need for **scheduled** (not purely event-triggered) work — periodic sweeps for reminders ("assessment due in 24h") and expiry ("deadline passed, auto-submit or mark expired"). Recommend introducing **Celery beat** at this point, scoped narrowly to two periodic tasks:
- `assessment_expiry_worker.sweep_expired_sessions` — runs frequently (e.g. every 5 min), finds sessions/invitations past deadline, transitions them to `Expired`, auto-submits in-progress attempts.
- `assessment_invitation_worker.sweep_pending_reminders` — runs hourly, finds invitations approaching their deadline unsent a reminder, enqueues `send_reminder_email`.

**Retries**: email sends use Celery's built-in retry with backoff (`autoretry_for=(SMTPException,), retry_backoff=True`) — a new pattern for this codebase (existing workers are DB/AI calls, not third-party network calls), isolated to the notification workers so it doesn't affect `resume_parser`/`embedding_worker` retry semantics.

**Failure recovery**: failed sends are logged to `AssessmentAuditLog` with the failure reason and surfaced as a "resend" affordance in the recruiter's progress table — no silent failures, no automatic infinite retry.

---

## 11. Notification Strategy

Built as a `StorageBackend`-style abstraction (`notifications/base.py: NotificationChannel`), because the platform already has a precedent for "one interface, swappable backend, selected via factory":

```
NotificationService (in services/)
        │
        ▼
NotificationChannel (ABC: send(notification) -> None)
        │
   ┌────┴────┬─────────────┬─────────────┐
 Email     In-App        SMS (later)   Teams/Slack (later)
(built)   (built, backs   (seam only,  (seam only, same
           existing FE     no channel    interface)
           stubs)          class yet)
```

- **Email**: `EmailChannel`, sends via whatever the platform's existing outbound-email mechanism is (invitation sent, reminder, completion notice to recruiter).
- **In-app**: writes an `AppNotification` row + (if the platform has a push mechanism already, e.g. websocket/poll — otherwise TanStack Query poll on `use-notifications.ts`, which already exists) so the bell/badge in the dashboard lights up. This is the channel the frontend's `notification-store.tsx` and `use-notifications.ts` are already built to consume.
- **SMS / Teams / Slack**: explicitly out of scope for 5.1 — listed here only to confirm the abstraction doesn't need to change shape to add them later; each is a new `NotificationChannel` subclass plus a factory entry, zero changes to callers.

**Event propagation**: lifecycle transitions in `AssessmentService`/`CandidateSessionService`/`AssessmentInvitationService` call `NotificationService.notify(event_type, context)` synchronously in the service method (consistent with how those services already call other services), which fans out to Celery for the actual channel dispatch (so a slow email provider never blocks the API response) — same pattern as `resume_parser.py` self-enqueuing the embedding task.

---

## 12. Security

| Concern | Approach |
|---|---|
| **Assessment links** | Signed token (server-side secret, not guessable), embedding invitation id + org id + expiry claim; verified by `RequireInvitationToken` on every candidate-facing request — never trust a client-supplied org_id. |
| **Expiration** | Hard expiry timestamp on the invitation (separate from the Assessment's time-limit-per-attempt); expired tokens fail verification server-side regardless of what the frontend shows — no client-only expiry checks. |
| **Replay prevention** | Token is single-use for *starting* a session (a `jti`-equivalent claim marked consumed in `AssessmentInvitation` on first `start()`); subsequent requests within the same session are authorized by a session-scoped credential (short-lived, issued at start-time), not by replaying the original invitation token — so a leaked "in-progress" request can't be used to restart a finished attempt. |
| **Tampering** | Token is signed (HMAC/JWT-style, consistent with however the platform already signs its auth JWTs) — any modified claim (org id, invitation id, expiry) fails signature verification before touching the DB. |
| **Audit logs** | `AssessmentAuditLog`: append-only record of token issuance, token verification (success/failure), session start, submit, and any recruiter action (revoke, resend) — this is the same "compliance trail" instinct as the rest of an enterprise platform, just newly instantiated for this module. |
| **Tenant isolation** | Every candidate-facing repository call still receives an explicit `org_id` — sourced from the verified token's claim, not from any client input — preserving the platform-wide invariant that no query is ever unscoped. |
| **Authorization** | Two independent primitives, never conflated: `RequireRoles` (recruiter/admin, JWT-based) and `RequireInvitationToken` (candidate, link-based). A candidate token can never satisfy a `RequireRoles` check and vice versa. |
| **Rate limiting** | Candidate-facing endpoints (especially token verification) should be rate-limited per-token/per-IP (Redis-backed counter, reusing the existing Redis dependency already in `core/redis.py`) to blunt token-guessing/brute-force attempts, since these endpoints are unauthenticated by design. |

---

## 13. Scalability

- **Stateless API**: recruiter and candidate routers are both stateless FastAPI endpoints — horizontal scaling is a load-balancer/replica-count concern only, no architectural change needed.
- **Concurrent submissions**: autosave writes (candidate answers) are the highest-frequency write path in this module — debounce client-side (already planned in `use-candidate-session.ts`) and consider upsert-per-question rather than append-only history to bound write volume per session.
- **Queue design**: dedicate a `notifications` Celery queue (separate from `resumes`/`embeddings`) so a burst of invitation emails for a large candidate pool never delays resume/JD parsing throughput, and vice versa — workers can be scaled independently per queue.
- **Celery beat sweep frequency**: tune `sweep_expired_sessions` interval against expected session volume — at "thousands of concurrent candidates," a 5-minute sweep over an indexed `(status, expires_at)` column is cheap; avoid a naive full-table scan.
- **Caching**: token verification is on the hot path for every candidate request — cache verified-token → org/invitation context in Redis with a TTL bounded by the token's own expiry, avoiding a DB round-trip per request during an active session.
- **Indexing plan (conceptual, no DDL here)**: composite index on `(org_id, status)` for Assessment/Invitation dashboard queries; index on the invitation token's lookup key; index on `(session_id, question_id)` for answer upserts.
- **Horizontal scaling of workers**: notification and expiry-sweep workers scale independently from the existing resume/embedding workers since they're on a separate queue — no shared bottleneck.

---

## 14. API Planning (endpoint inventory — no implementations)

**Assessments** (`/api/v1/assessments`, `RequireRoles`)
- `POST /assessments` — create
- `GET /assessments` — list (org-scoped, filterable by status)
- `GET /assessments/{id}` — detail
- `PATCH /assessments/{id}` — update (pre-publish only)
- `POST /assessments/{id}/publish`
- `POST /assessments/{id}/archive`
- `DELETE /assessments/{id}` — soft delete

**Templates** (`/api/v1/assessment-templates`, `RequireRoles`)
- `POST /assessment-templates`
- `GET /assessment-templates` — includes platform-library templates for eligible roles
- `GET /assessment-templates/{id}`
- `PATCH /assessment-templates/{id}`
- `POST /assessment-templates/{id}/duplicate`
- `DELETE /assessment-templates/{id}`

**Questions** (nested under Assessment or Template, `RequireRoles`)
- `POST /assessments/{id}/questions`
- `PATCH /assessments/{id}/questions/{question_id}`
- `POST /assessments/{id}/questions/reorder`
- `DELETE /assessments/{id}/questions/{question_id}`
- (mirrored under `/assessment-templates/{id}/questions/...`)

**Invitations** (`/api/v1/assessments/{id}/invitations`, `RequireRoles`)
- `POST /assessments/{id}/invitations` — bulk send
- `GET /assessments/{id}/invitations` — list with status
- `POST /assessments/{id}/invitations/{invitation_id}/resend`
- `POST /assessments/{id}/invitations/{invitation_id}/revoke`

**Progress/Monitoring** (`/api/v1/assessments/{id}/progress`, `RequireRoles`)
- `GET /assessments/{id}/progress` — funnel aggregate
- `GET /assessments/{id}/sessions/{session_id}` — recruiter review view of one candidate's answers
- `POST /assessments/{id}/sessions/{session_id}/complete` — mark reviewed

**Candidate-facing** (`/api/v1/public/assessments/{token}`, `RequireInvitationToken`)
- `GET /public/assessments/{token}` — landing/instructions data
- `POST /public/assessments/{token}/start`
- `GET /public/assessments/{token}/session` — resume in-progress session
- `POST /public/assessments/{token}/answers` — autosave one answer
- `POST /public/assessments/{token}/submit`

**Notifications** (`/api/v1/notifications`, authenticated)
- `GET /notifications`
- `POST /notifications/mark-read`
- `POST /notifications/mark-all-read`

---

## 15. UI/UX

Reuses the existing dark-theme `components/ui/` kit and `design-system/tokens/` exactly as-is — no new visual language introduced without going through the token layer first.

- **Assessment list/detail pages**: `data-table.tsx` + `statistic-card.tsx` (funnel counts), `card.tsx` for assessment tiles — identical composition to the Campaigns list/detail pages today.
- **Builder wizard**: multi-step form using existing form primitives + React Hook Form + Zod, consistent with `campaign-form.tsx`'s validation pattern.
- **Candidate runner**: a deliberately minimal, distraction-free layout — no dashboard chrome — but still built from the same `components/ui/` primitives (buttons, cards, progress indicators) so it doesn't look like a foreign app; just a stripped-down layout, not a different design system.
- **Glassmorphism note**: current tokens don't include blur/translucency values. If this visual treatment is wanted for the candidate-facing runner (a reasonable place to want it — it's the most "external-facing" screen in the platform), it should be added as new tokens in `design-system/tokens/` (e.g. an `elevation`/`surface-blur` token set) so every future consumer gets it for free, rather than hardcoded `backdrop-blur` classes on one page.
- **Responsiveness**: candidate runner must work on mobile (uncontrolled candidate devices) — timer banner and question navigator need mobile-first layout, not just a squeeze of the desktop layout.

---

## 16. Future Compatibility — Phase 6 AI Interview Agent

This module is deliberately shaped so Phase 6 is additive, not a redesign:

- **`CandidateAssessmentSession` / `CandidateAnswer`** are the substrate an interview agent extends — an "interview" is modeled as another session type (or another Assessment Question type: "verbal response") reusing the exact same start/answer/submit lifecycle, invitation/token security model, and progress-tracking dashboard. No new session concept needed.
- **`AssessmentScoringService`** (placeholder, no-op in 5.1) is the pre-agreed seam where Phase 6's AI scoring pipeline attaches — it already sits in the Service layer with access to Sessions/Answers, so adding real scoring logic (LLM-based transcript analysis, semantic answer comparison via the existing pgvector/embedding worker pattern) touches one file, not the routers, repositories, or frontend contracts.
- **`StorageBackend`** already supports arbitrary binary artifacts (resumes today); Phase 6's audio/video interview recordings plug into the same abstraction with a new `save()` call, no new storage concept.
- **`RequireInvitationToken`** and the candidate-facing route group/API prefix generalize directly to "join an interview session" — same token issuance, same expiry/replay/tamper protections, same separate unauthenticated frontend shell.
- **Notification channels** (email/in-app, extensible to SMS/Teams/Slack) reuse as-is for interview scheduling and reminders — no new notification concept, just new event types flowing through the same `NotificationService`.
- **Celery beat + dedicated queue** infrastructure introduced in 5.1 for reminders/expiry is exactly what interview scheduling (send reminder N hours before a live/AI interview) will need — Phase 6 adds tasks to the existing `notifications` queue rather than needing new worker infrastructure.
- **Permission model** requires zero changes: `RequireRoles` for recruiter-side interview management, `RequireInvitationToken` for candidate-side access — both already generalized past "assessment" specifically.

Net effect: Phase 6 should be able to add an "Interview" as a specialization of Assessment/Session, plug a real scoring engine into the existing seam, and add a new storage artifact type and channel — without touching the Router→Service→Repository→DB architecture, without new RBAC primitives, and without a new security model.
