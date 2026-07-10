"""
Celery task: generate_communication_assessment
────────────────────────────────────────────────
Deterministic aggregation of one AssessmentSession's Read Aloud + Listen &
Repeat AssessmentAnalysis rows into a single recruiter-facing
CommunicationAssessment. Dispatched automatically right after either
analyze_read_aloud or analyze_listen_repeat completes (see
app.workers.communication_analysis) — whichever of the two finishes last is
what actually triggers scoring, since this task waits for both.

Does NOT re-run Whisper, does NOT re-run embeddings, does NOT call an LLM —
consumes only already-persisted AssessmentAnalysis rows. Scoring itself is
app.ai.communication.communication_assessment_engine.CommunicationAssessmentEngine.

Phase 1 (own transaction) — Fetch the AssessmentSession, create (idempotently)
          the CommunicationAssessment row (PENDING as soon as the session is
          known to exist, so recruiters can observe PENDING before both
          analyses land). If already COMPLETED, skip (idempotent — this is
          how duplicate processing from both sibling tasks dispatching this
          task is avoided). If either sibling AssessmentAnalysis is missing
          or not yet COMPLETED, return silently — not an error, just not
          ready yet; whichever analysis finishes later will re-dispatch.
          If either sibling FAILED, mark this assessment FAILED and stop
          (retrying this task can't fix an upstream permanent failure).
Phase 2 (no DB) — Score via CommunicationAssessmentEngine (pure Python).
Phase 3 (own transaction) — Persist scores/strengths/improvements/summary,
          mark COMPLETED.

Retry policy: up to 3 retries with the same exponential backoff as every
other worker in this codebase (30s, 60s, 120s) — this task has no external
I/O beyond two DB transactions, so a failure partway through is almost
always a transient DB hiccup rather than a permanent input problem (unlike
analyze_read_aloud/analyze_listen_repeat, there's no equivalent of an
"invalid duration" permanent-failure class here).
"""

import logging
import uuid
from typing import Any

from celery import Task
from sqlalchemy import select

from app.ai.communication.communication_assessment_engine import CommunicationAssessmentEngine
from app.ai.communication.schemas import ListenRepeatAssessmentInput, ReadAloudAssessmentInput
from app.db.session import AsyncSessionLocal
from app.models.assessment_analysis import AnalysisStatus, AnalysisType, AssessmentAnalysis
from app.models.assessment_recording import AssessmentRecording
from app.models.assessment_session import AssessmentSession
from app.models.assessment_transcript import AssessmentTranscript
from app.models.candidate_activity import ActivityEventType
from app.models.communication_assessment import CommunicationAssessmentStatus
from app.models.notification import NotificationType
from app.models.resume_file import PipelineStage, ResumeFile
from app.repositories.campaign import CampaignRepository
from app.repositories.candidate import CandidateRepository
from app.repositories.candidate_activity import CandidateActivityRepository
from app.repositories.communication_assessment import CommunicationAssessmentRepository
from app.repositories.notification import NotificationRepository
from app.repositories.notification_preference import NotificationPreferenceRepository
from app.repositories.resume_file import ResumeFileRepository
from app.services.communication_assessment import CommunicationAssessmentService
from app.services.notification import NotificationService
from app.services.notification_preference import should_notify
from app.services.pipeline_transitions import advance_pipeline_stage
from app.workers.celery_app import celery_app, run_task

logger = logging.getLogger(__name__)


# ── Private helpers ───────────────────────────────────────────────────────────


async def _get_analyses_for_session(
    session: Any, assessment_session_id: uuid.UUID
) -> dict[AnalysisType, AssessmentAnalysis]:
    """Fetch every AssessmentAnalysis belonging to one session, keyed by
    analysis_type, by joining transcript -> recording -> session. Mirrors the
    join style of speech_transcription._get_recording_with_org."""
    result = await session.execute(
        select(AssessmentAnalysis)
        .join(AssessmentTranscript, AssessmentAnalysis.transcript_id == AssessmentTranscript.id)
        .join(AssessmentRecording, AssessmentTranscript.recording_id == AssessmentRecording.id)
        .where(AssessmentRecording.session_id == assessment_session_id)
    )
    return {row.analysis_type: row for row in result.scalars().all()}


async def _notify_assessment_completed(
    session: Any,
    resume_file: ResumeFile,
    *,
    candidate_id: uuid.UUID,
    campaign_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    """Best-effort: notify the assigned recruiter (falling back to the
    campaign's creator if nobody is assigned) that this candidate's
    assessment finished. Never raises — a notification failure must not
    fail the assessment-completion transaction it's riding along in."""
    campaign_repo = CampaignRepository(session)
    campaign = await campaign_repo.get_by_id(campaign_id, org_id)

    recipient_id = resume_file.assigned_recruiter_id or (
        campaign.created_by if campaign is not None else None
    )
    if recipient_id is None:
        logger.info(
            "No recruiter to notify (unassigned candidate, campaign has no creator)",
            extra={"resume_file_id": str(resume_file.id)},
        )
        return

    candidate_repo = CandidateRepository(session)
    candidate = await candidate_repo.get_by_id_and_org(candidate_id, org_id)
    candidate_name = f"{candidate.first_name} {candidate.last_name}" if candidate else "A candidate"
    campaign_title = campaign.title if campaign is not None else "your campaign"

    try:
        # A SAVEPOINT (not the outer transaction): if the insert below fails
        # mid-flush, only this savepoint rolls back — the caller's session
        # stays healthy for its own commit (pipeline_stage/complete_processing
        # must survive even if this notification doesn't).
        async with session.begin_nested():
            prefs_repo = NotificationPreferenceRepository(session)
            in_app_allowed, _email_allowed = await should_notify(
                prefs_repo, recipient_id, "assessment_completed"
            )
            if not in_app_allowed:
                logger.info(
                    "Skipping assessment-completed notification — recipient has it disabled",
                    extra={"resume_file_id": str(resume_file.id), "recipient_id": str(recipient_id)},
                )
                return
            notification_service = NotificationService(NotificationRepository(session))
            await notification_service.create(
                organization_id=org_id,
                user_id=recipient_id,
                type=NotificationType.SUCCESS,
                title="Assessment Completed",
                message=f"{candidate_name} completed their communication assessment for {campaign_title}.",
                resume_file_id=resume_file.id,
            )
    except Exception:
        logger.warning(
            "Failed to create assessment-completed notification",
            extra={"resume_file_id": str(resume_file.id)},
            exc_info=True,
        )


# ── Core async implementation ─────────────────────────────────────────────────


async def _run_generate_communication_assessment(
    session_id_str: str,
    *,
    _session_factory: Any = None,
    _engine: Any = None,
) -> None:
    """Full Communication Assessment aggregation workflow. Accepts optional
    overrides for testability."""
    factory = _session_factory or AsyncSessionLocal
    engine = _engine or CommunicationAssessmentEngine()
    assessment_session_id = uuid.UUID(session_id_str)
    log_ctx = {"assessment_session_id": session_id_str}

    # ── Phase 1: Ensure session exists, create/fetch the assessment row,
    #             check whether both sibling analyses are ready ────────────
    async with factory() as session:
        assessment_session = await session.get(AssessmentSession, assessment_session_id)
        if assessment_session is None:
            logger.warning("AssessmentSession not found — nothing to do", extra=log_ctx)
            return

        repo = CommunicationAssessmentRepository(session)
        service = CommunicationAssessmentService(repo)
        assessment = await service.create_pending(assessment_session_id, assessment_session.org_id)
        await session.commit()

        if assessment.status == CommunicationAssessmentStatus.COMPLETED:
            logger.info("Assessment already completed — idempotent skip", extra=log_ctx)
            return

        analyses = await _get_analyses_for_session(session, assessment_session_id)
        read_aloud = analyses.get(AnalysisType.READ_ALOUD)
        listen_repeat = analyses.get(AnalysisType.LISTEN_REPEAT)

        if read_aloud is None or listen_repeat is None:
            logger.info("Waiting on sibling analysis — not ready yet", extra=log_ctx)
            return

        if read_aloud.status == AnalysisStatus.FAILED or listen_repeat.status == AnalysisStatus.FAILED:
            failed_parts = [
                label
                for label, row in (
                    ("Read Aloud", read_aloud),
                    ("Listen & Repeat", listen_repeat),
                )
                if row.status == AnalysisStatus.FAILED
            ]
            error_message = (
                f"{' and '.join(failed_parts)} analysis failed; "
                "cannot generate communication assessment."
            )
            await service.fail_processing(assessment_session_id, error_message)
            await session.commit()
            logger.warning("Upstream analysis failed — assessment marked FAILED", extra=log_ctx)
            return

        if (
            read_aloud.status != AnalysisStatus.COMPLETED
            or listen_repeat.status != AnalysisStatus.COMPLETED
        ):
            logger.info("Sibling analyses not both COMPLETED yet — not ready", extra=log_ctx)
            return

        logger.info("Task Started", extra={**log_ctx, "assessment_id": str(assessment.id)})

        # Capture scalars before the session closes (expire_on_commit=False preserves them)
        candidate_id = assessment_session.candidate_id
        campaign_id = assessment_session.campaign_id
        org_id = assessment_session.org_id
        read_aloud_input = ReadAloudAssessmentInput(
            overall_score=read_aloud.overall_score,
            word_accuracy=read_aloud.word_accuracy,
            reading_speed_wpm=read_aloud.reading_speed_wpm,
            completion_percentage=read_aloud.completion_percentage,
        )
        listen_repeat_input = ListenRepeatAssessmentInput(
            overall_score=listen_repeat.overall_score,
            semantic_similarity=listen_repeat.semantic_similarity,
            keyword_coverage=listen_repeat.keyword_coverage,
            completion_percentage=listen_repeat.completion_percentage,
        )

    # ── Phase 2: Score (no DB, no LLM) ─────────────────────────────────────
    result = engine.assess(read_aloud_input, listen_repeat_input)

    # ── Phase 3: Persist results ────────────────────────────────────────────
    async with factory() as session:
        repo = CommunicationAssessmentRepository(session)
        service = CommunicationAssessmentService(repo)
        await service.complete_processing(
            assessment_session_id,
            overall_score=result.overall_score,
            reading_score=result.reading_score,
            listening_score=result.listening_score,
            confidence_score=result.confidence_score,
            strengths_json=result.strengths,
            improvements_json=result.improvements,
            summary_json=result.summary.model_dump(mode="json"),
        )

        # Only after the CommunicationAssessment itself is COMPLETED — never
        # merely because uploads/transcription finished (see PART 2 of the
        # automatic-pipeline-workflow sprint doc).
        resume_file = await advance_pipeline_stage(
            ResumeFileRepository(session),
            CandidateActivityRepository(session),
            candidate_id=candidate_id,
            campaign_id=campaign_id,
            target_stage=PipelineStage.ASSESSMENT_COMPLETED,
            event_type=ActivityEventType.ASSESSMENT_COMPLETED,
        )
        if resume_file is not None:
            await _notify_assessment_completed(
                session,
                resume_file,
                candidate_id=candidate_id,
                campaign_id=campaign_id,
                org_id=org_id,
            )

        await session.commit()
        logger.info(
            "Task Completed",
            extra={**log_ctx, "overall_score": result.overall_score},
        )


async def _mark_failed(
    session_id_str: str,
    error: str,
    *,
    _session_factory: Any = None,
) -> None:
    """Best-effort: set the CommunicationAssessment status to FAILED with an
    error message."""
    factory = _session_factory or AsyncSessionLocal
    try:
        assessment_session_id = uuid.UUID(session_id_str)
        async with factory() as session:
            repo = CommunicationAssessmentRepository(session)
            service = CommunicationAssessmentService(repo)
            await service.fail_processing(assessment_session_id, error[:1000])
            await session.commit()
    except Exception as exc:
        logger.error(
            "Task Failed — could not persist FAILED status",
            extra={"assessment_session_id": session_id_str, "mark_error": str(exc)},
        )


# ── Celery task (sync entry point) ────────────────────────────────────────────


async def _run_generate_communication_assessment_with_recovery(session_id: str) -> None:
    """Runs the aggregation workflow and, on failure, persists the FAILED
    status in the same coroutine/event loop as the work itself (see
    celery_app.run_task's docstring for why a second, separate asyncio.run()
    call for _mark_failed is unsafe)."""
    try:
        await _run_generate_communication_assessment(session_id)
    except Exception as exc:
        await _mark_failed(session_id, str(exc)[:1000])
        raise


def _generate_communication_assessment_task(self: Task, session_id: str) -> None:
    """
    Core task logic extracted from the decorator for direct testability.
    Every failure here is transient (DB hiccup) — there's no permanent-error
    class to classify separately, unlike analyze_read_aloud/analyze_listen_repeat.
    """
    log_ctx = {"assessment_session_id": session_id, "attempt": self.request.retries + 1}
    logger.info("Task started", extra=log_ctx)

    try:
        run_task(_run_generate_communication_assessment_with_recovery(session_id))
        logger.info("Task completed", extra=log_ctx)

    except Exception as exc:
        countdown = 30 * (2 ** self.request.retries)
        logger.warning(
            "Task Retried",
            extra={**log_ctx, "error": str(exc), "countdown_s": countdown},
        )
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(
    bind=True,
    name="app.workers.communication_assessment.generate_communication_assessment",
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
)
def generate_communication_assessment(self: Task, session_id: str) -> None:
    """Entry point registered with Celery. Delegates to
    _generate_communication_assessment_task."""
    _generate_communication_assessment_task(self, session_id)
