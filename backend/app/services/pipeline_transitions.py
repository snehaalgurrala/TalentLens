"""Shared "advance a candidate's pipeline stage automatically" helper for
the three new backend-driven assessment transitions (invitation sent,
invitation opened, communication assessment completed — see
docs/phase5-sprint5.8-automatic-pipeline-workflow.md).

Deliberately the same nudge-forward-only + activity-log shape already used
inline by app.workers.resume_parser / app.workers.embedding_worker /
CandidateManagementService._set_review_status, centralized here so the three
NEW call sites don't each reimplement it. Those pre-existing, already-tested
call sites are left untouched.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from app.models.candidate_activity import ActivityEventType
from app.models.resume_file import PipelineStage, ResumeFile, is_earlier_pipeline_stage

if TYPE_CHECKING:
    from app.repositories.candidate_activity import CandidateActivityRepository
    from app.repositories.resume_file import ResumeFileRepository


async def advance_pipeline_stage(
    resume_file_repo: ResumeFileRepository,
    activity_repo: CandidateActivityRepository,
    *,
    candidate_id: uuid.UUID,
    campaign_id: uuid.UUID,
    target_stage: PipelineStage,
    event_type: ActivityEventType,
) -> ResumeFile | None:
    """Look up the (candidate, campaign) ResumeFile row and nudge its
    pipeline_stage forward to `target_stage`, logging `event_type`.

    Returns None if no matching ResumeFile row exists (nothing to advance —
    not an error, since not every candidate_id/campaign_id pairing this gets
    called with is guaranteed to have one, e.g. a stale/edge-case invitation).
    Never moves the stage backward — a late-arriving event for a candidate a
    recruiter already moved further along (e.g. straight to Rejected) is a
    silent no-op, same guarantee every other pipeline_stage nudge in this
    codebase already provides.
    """
    resume_file = await resume_file_repo.get_by_candidate_and_campaign(candidate_id, campaign_id)
    if resume_file is None:
        return None

    if not is_earlier_pipeline_stage(resume_file.pipeline_stage, target_stage):
        return resume_file

    updated = await resume_file_repo.update(resume_file, pipeline_stage=target_stage)
    await activity_repo.create(resume_file.id, None, event_type)
    return updated
