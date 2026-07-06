"""
CandidateManagementService — the full ATS candidate list behind
/campaigns/{id}/candidates, plus the single/bulk recruiter actions
(pipeline stage, recruiter assignment, notes, shortlist/reject/delete)
that /candidates exposes.

Wraps CandidateRankingService rather than duplicating scoring: ranking is
attempted once per call, and a campaign with no ready job description is a
normal state (ranking_available=False, not an error) — every resume file
still appears in the list with its real upload/pipeline status and null
score fields, never a fabricated score.

Filtering, search, and sorting all happen in memory over the campaign's
full resume-file set (bounded per campaign, same scale assumption already
made by CandidateRankingService.rank_campaign), so a search across
candidate name/email/phone/company/skills/designation/college can see the
whole set rather than only whatever page happens to be requested.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from fastapi import HTTPException, status

from app.models.candidate_activity import ActivityEventType
from app.models.resume_file import PipelineStage, ReviewStatus, is_earlier_pipeline_stage
from app.schemas.candidate_management import (
    BulkActionFailure,
    BulkActionResult,
    CandidateListItem,
    CandidateListResponse,
    EducationItem,
)
from app.schemas.candidate_ranking import RankingSubScores
from app.schemas.user import UserSummaryResponse

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.resume_file import ResumeFile
    from app.models.user import User
    from app.repositories.campaign import CampaignRepository
    from app.repositories.candidate import CandidateRepository
    from app.repositories.parsed_resume import ParsedResumeRepository
    from app.repositories.candidate_activity import CandidateActivityRepository
    from app.repositories.resume_file import ResumeFileRepository
    from app.repositories.user import UserRepository
    from app.services.candidate_ranking import CandidateRankingEntry, CandidateRankingService

SortField = Literal["overall_score", "candidate_name", "applied_at", "years_of_experience"]


@dataclass(frozen=True)
class _MergedRow:
    resume_file: ResumeFile
    candidate: Candidate | None
    entry: CandidateRankingEntry | None
    skills: list[str]
    education: list[EducationItem]


class CandidateManagementService:
    def __init__(
        self,
        resume_file_repo: ResumeFileRepository,
        candidate_repo: CandidateRepository,
        parsed_resume_repo: ParsedResumeRepository,
        campaign_repo: CampaignRepository,
        user_repo: UserRepository,
        ranking_service: CandidateRankingService,
        activity_repo: CandidateActivityRepository | None = None,
    ) -> None:
        self.resume_file_repo = resume_file_repo
        self.candidate_repo = candidate_repo
        self.parsed_resume_repo = parsed_resume_repo
        self.campaign_repo = campaign_repo
        self.user_repo = user_repo
        self.ranking_service = ranking_service
        self.activity_repo = activity_repo

    # ── Internal guards ──────────────────────────────────────────────────────

    def _require_org(self, user: User) -> uuid.UUID:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to manage candidates.",
            )
        return user.org_id

    async def _require_campaign(self, campaign_id: uuid.UUID, org_id: uuid.UUID):
        campaign = await self.campaign_repo.get_by_id(campaign_id, org_id)
        if campaign is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found.",
            )
        return campaign

    async def _require_resume_file(self, resume_file_id: uuid.UUID, user: User) -> ResumeFile:
        """Fetch a resume file and verify it belongs to the user's org via its
        campaign — the critical multi-tenant guard for every single/bulk
        action, since resume_file_id alone doesn't carry org context."""
        org_id = self._require_org(user)
        rf = await self.resume_file_repo.get_by_id(resume_file_id)
        if rf is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found."
            )
        await self._require_campaign(rf.campaign_id, org_id)
        return rf

    # ── List ──────────────────────────────────────────────────────────────────

    async def list_campaign_candidates(
        self,
        campaign_id: uuid.UUID,
        user: User,
        *,
        search: str | None = None,
        pipeline_stage: PipelineStage | None = None,
        review_status: ReviewStatus | None = None,
        assigned_recruiter_id: uuid.UUID | None = None,
        sort_by: SortField = "overall_score",
        sort_dir: Literal["asc", "desc"] = "desc",
        skip: int = 0,
        limit: int = 50,
    ) -> CandidateListResponse:
        org_id = self._require_org(user)
        await self._require_campaign(campaign_id, org_id)

        ranking_available = True
        try:
            entries = await self.ranking_service.rank_campaign(campaign_id, user)
        except HTTPException:
            entries = []
            ranking_available = False
        entries_by_resume_file = {e.resume_file_id: e for e in entries}

        resume_files = await self.resume_file_repo.list_by_campaign(campaign_id)
        candidate_ids = [rf.candidate_id for rf in resume_files if rf.candidate_id is not None]
        candidates_by_id = {c.id: c for c in await self.candidate_repo.list_by_ids(candidate_ids)}

        parsed_resumes = await self.parsed_resume_repo.list_by_resume_file_ids(
            [rf.id for rf in resume_files]
        )
        parsed_by_resume_file = {pr.resume_file_id: pr for pr in parsed_resumes}

        recruiter_ids = [
            rf.assigned_recruiter_id for rf in resume_files if rf.assigned_recruiter_id is not None
        ]
        recruiters_by_id = {}
        if recruiter_ids:
            for rid in set(recruiter_ids):
                recruiter = await self.user_repo.get_by_id(rid)
                if recruiter is not None:
                    recruiters_by_id[rid] = recruiter

        rows = [
            self._merge_row(rf, candidates_by_id, entries_by_resume_file, parsed_by_resume_file)
            for rf in resume_files
        ]

        if search:
            needle = search.strip().lower()
            rows = [r for r in rows if needle and self._matches_search(r, needle)]
        if pipeline_stage is not None:
            rows = [r for r in rows if r.resume_file.pipeline_stage == pipeline_stage]
        if review_status is not None:
            rows = [r for r in rows if r.resume_file.review_status == review_status]
        if assigned_recruiter_id is not None:
            rows = [
                r for r in rows if r.resume_file.assigned_recruiter_id == assigned_recruiter_id
            ]

        rows.sort(key=lambda r: self._sort_key(r, sort_by), reverse=(sort_dir == "desc"))

        total = len(rows)
        page = rows[skip : skip + limit]

        items = [
            self._to_list_item(r, recruiters_by_id.get(r.resume_file.assigned_recruiter_id))
            for r in page
        ]
        return CandidateListResponse(
            items=items, total=total, skip=skip, limit=limit, ranking_available=ranking_available
        )

    def _merge_row(self, rf, candidates_by_id, entries_by_resume_file, parsed_by_resume_file) -> _MergedRow:
        candidate = candidates_by_id.get(rf.candidate_id) if rf.candidate_id else None
        entry = entries_by_resume_file.get(rf.id)
        parsed = parsed_by_resume_file.get(rf.id)
        structured_resume = {}
        if parsed is not None and parsed.structured_json:
            structured_resume = parsed.structured_json.get("structured_resume") or {}
        skills = [s for s in (structured_resume.get("skills") or []) if s]
        education = [
            EducationItem(
                institution=e.get("institution"), degree=e.get("degree"), field=e.get("field")
            )
            for e in (structured_resume.get("education") or [])
        ]
        return _MergedRow(
            resume_file=rf, candidate=candidate, entry=entry, skills=skills, education=education
        )

    def _matches_search(self, row: _MergedRow, needle: str) -> bool:
        haystack_parts: list[str] = [row.resume_file.original_filename]
        if row.candidate is not None:
            c = row.candidate
            haystack_parts.extend(
                filter(
                    None,
                    [
                        f"{c.first_name} {c.last_name}",
                        c.email,
                        c.phone,
                        c.current_company,
                        c.current_role,
                    ],
                )
            )
        haystack_parts.extend(row.skills)
        haystack_parts.extend(e.institution or "" for e in row.education)
        return needle in " ".join(haystack_parts).lower()

    def _sort_key(self, row: _MergedRow, sort_by: SortField):
        if sort_by == "overall_score":
            return row.entry.overall_score if row.entry is not None else -1.0
        if sort_by == "candidate_name":
            name = self._candidate_name(row)
            return name.lower()
        if sort_by == "applied_at":
            return row.resume_file.uploaded_at
        if sort_by == "years_of_experience":
            return row.candidate.years_of_experience if row.candidate is not None else -1.0
        return 0

    def _candidate_name(self, row: _MergedRow) -> str:
        if row.candidate is not None:
            return f"{row.candidate.first_name} {row.candidate.last_name}".strip()
        return row.resume_file.original_filename

    def _to_list_item(self, row: _MergedRow, recruiter) -> CandidateListItem:
        entry = row.entry
        return CandidateListItem(
            resume_file_id=row.resume_file.id,
            candidate_id=row.candidate.id if row.candidate else row.resume_file.id,
            candidate_name=self._candidate_name(row),
            email=row.candidate.email if row.candidate else None,
            phone=row.candidate.phone if row.candidate else None,
            location=row.candidate.location if row.candidate else None,
            current_company=row.candidate.current_company if row.candidate else None,
            current_role=row.candidate.current_role if row.candidate else None,
            years_of_experience=row.candidate.years_of_experience if row.candidate else None,
            skills=row.skills,
            education=row.education,
            rank=entry.rank if entry else None,
            overall_score=entry.overall_score if entry else None,
            sub_scores=(
                RankingSubScores(
                    semantic_score=entry.match_result.semantic_score,
                    skills_score=entry.match_result.skills_score,
                    experience_score=entry.match_result.experience_score,
                    education_score=entry.match_result.education_score,
                    projects_score=entry.match_result.projects_score,
                    certification_score=entry.match_result.certification_score,
                )
                if entry
                else None
            ),
            recommendation=entry.recommendation if entry else None,
            upload_status=row.resume_file.upload_status,
            review_status=row.resume_file.review_status,
            pipeline_stage=row.resume_file.pipeline_stage,
            assigned_recruiter=(
                UserSummaryResponse.model_validate(recruiter) if recruiter is not None else None
            ),
            notes=row.resume_file.notes,
            applied_at=row.resume_file.uploaded_at,
        )

    # ── Single-record actions ────────────────────────────────────────────────

    async def update_pipeline_stage(
        self, resume_file_id: uuid.UUID, pipeline_stage: PipelineStage, user: User
    ) -> ResumeFile:
        rf = await self._require_resume_file(resume_file_id, user)
        from_stage = rf.pipeline_stage
        updated = await self.resume_file_repo.update(rf, pipeline_stage=pipeline_stage)
        if self.activity_repo is not None:
            await self.activity_repo.create(
                rf.id,
                user.id,
                ActivityEventType.PIPELINE_STAGE_CHANGED,
                {"from_stage": from_stage.value, "to_stage": pipeline_stage.value},
            )
        return updated

    async def assign_recruiter(
        self, resume_file_id: uuid.UUID, assigned_recruiter_id: uuid.UUID | None, user: User
    ) -> ResumeFile:
        rf = await self._require_resume_file(resume_file_id, user)
        previous_recruiter_id = rf.assigned_recruiter_id
        if assigned_recruiter_id is not None:
            recruiter = await self.user_repo.get_by_id(assigned_recruiter_id)
            if recruiter is None or recruiter.org_id != user.org_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Recruiter not found in your organization.",
                )
        updated = await self.resume_file_repo.update(
            rf, assigned_recruiter_id=assigned_recruiter_id
        )
        if self.activity_repo is not None and assigned_recruiter_id is not None:
            metadata: dict = {"assigned_recruiter_id": str(assigned_recruiter_id)}
            if previous_recruiter_id is not None and previous_recruiter_id != assigned_recruiter_id:
                metadata["from_recruiter_id"] = str(previous_recruiter_id)
            await self.activity_repo.create(
                rf.id, user.id, ActivityEventType.RECRUITER_ASSIGNED, metadata
            )
        return updated

    async def archive(self, resume_file_id: uuid.UUID, user: User) -> ResumeFile:
        rf = await self._require_resume_file(resume_file_id, user)
        from_stage = rf.pipeline_stage
        updated = await self.resume_file_repo.update(rf, pipeline_stage=PipelineStage.ARCHIVED)
        if self.activity_repo is not None:
            await self.activity_repo.create(
                rf.id,
                user.id,
                ActivityEventType.ARCHIVED,
                {"from_stage": from_stage.value, "to_stage": PipelineStage.ARCHIVED.value},
            )
        return updated

    async def restore(self, resume_file_id: uuid.UUID, user: User) -> ResumeFile:
        """Reverse a terminal stage (REJECTED/WITHDRAWN/ARCHIVED) back to the
        stage the candidate was in immediately before that terminal move, by
        walking the activity log for the most recent transition into the
        current stage. Falls back to APPLIED if no such history exists."""
        rf = await self._require_resume_file(resume_file_id, user)
        current_stage = rf.pipeline_stage
        if current_stage not in (
            PipelineStage.REJECTED,
            PipelineStage.WITHDRAWN,
            PipelineStage.ARCHIVED,
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Candidate is not in a terminal stage.",
            )
        target_stage = await self._resolve_restore_target(rf.id, current_stage)
        update_fields: dict = {"pipeline_stage": target_stage}
        if rf.review_status == ReviewStatus.REJECTED:
            update_fields["review_status"] = ReviewStatus.PENDING
        updated = await self.resume_file_repo.update(rf, **update_fields)
        if self.activity_repo is not None:
            await self.activity_repo.create(
                rf.id,
                user.id,
                ActivityEventType.RESTORED,
                {"from_stage": current_stage.value, "to_stage": target_stage.value},
            )
        return updated

    async def _resolve_restore_target(
        self, resume_file_id: uuid.UUID, current_stage: PipelineStage
    ) -> PipelineStage:
        if self.activity_repo is None:
            return PipelineStage.APPLIED
        history = await self.activity_repo.list_by_resume_file(resume_file_id)
        for event in history:
            meta = event.event_metadata or {}
            if (
                event.event_type
                in (ActivityEventType.PIPELINE_STAGE_CHANGED, ActivityEventType.ARCHIVED)
                and meta.get("to_stage") == current_stage.value
                and meta.get("from_stage")
            ):
                try:
                    return PipelineStage(meta["from_stage"])
                except ValueError:
                    break
        return PipelineStage.APPLIED

    async def update_notes(self, resume_file_id: uuid.UUID, notes: str | None, user: User) -> ResumeFile:
        rf = await self._require_resume_file(resume_file_id, user)
        return await self.resume_file_repo.update(rf, notes=notes)

    async def shortlist(self, resume_file_id: uuid.UUID, user: User) -> ResumeFile:
        return await self._set_review_status(resume_file_id, ReviewStatus.SHORTLISTED, user)

    async def reject(self, resume_file_id: uuid.UUID, user: User) -> ResumeFile:
        return await self._set_review_status(resume_file_id, ReviewStatus.REJECTED, user)

    async def _set_review_status(
        self, resume_file_id: uuid.UUID, review_status_value: ReviewStatus, user: User
    ) -> ResumeFile:
        rf = await self._require_resume_file(resume_file_id, user)
        target_stage = (
            PipelineStage.SHORTLISTED
            if review_status_value == ReviewStatus.SHORTLISTED
            else PipelineStage.REJECTED
        )
        stage_update = {}
        if is_earlier_pipeline_stage(rf.pipeline_stage, target_stage):
            stage_update["pipeline_stage"] = target_stage
        updated = await self.resume_file_repo.update(
            rf, review_status=review_status_value, **stage_update
        )
        if self.activity_repo is not None:
            event_type = (
                ActivityEventType.SHORTLISTED
                if review_status_value == ReviewStatus.SHORTLISTED
                else ActivityEventType.REJECTED
            )
            await self.activity_repo.create(rf.id, user.id, event_type)
        return updated

    async def delete(self, resume_file_id: uuid.UUID, user: User) -> None:
        rf = await self._require_resume_file(resume_file_id, user)
        await self.resume_file_repo.soft_delete(rf)

    # ── Bulk actions ──────────────────────────────────────────────────────────

    async def _bulk_apply(
        self, resume_file_ids: list[uuid.UUID], user: User, action
    ) -> BulkActionResult:
        succeeded: list[uuid.UUID] = []
        failed: list[BulkActionFailure] = []
        for resume_file_id in resume_file_ids:
            try:
                await action(resume_file_id)
                succeeded.append(resume_file_id)
            except HTTPException as exc:
                failed.append(BulkActionFailure(id=resume_file_id, reason=str(exc.detail)))
        return BulkActionResult(succeeded=succeeded, failed=failed)

    async def bulk_shortlist(self, resume_file_ids: list[uuid.UUID], user: User) -> BulkActionResult:
        return await self._bulk_apply(resume_file_ids, user, lambda rid: self.shortlist(rid, user))

    async def bulk_reject(self, resume_file_ids: list[uuid.UUID], user: User) -> BulkActionResult:
        return await self._bulk_apply(resume_file_ids, user, lambda rid: self.reject(rid, user))

    async def bulk_assign_recruiter(
        self, resume_file_ids: list[uuid.UUID], assigned_recruiter_id: uuid.UUID | None, user: User
    ) -> BulkActionResult:
        return await self._bulk_apply(
            resume_file_ids,
            user,
            lambda rid: self.assign_recruiter(rid, assigned_recruiter_id, user),
        )

    async def bulk_delete(self, resume_file_ids: list[uuid.UUID], user: User) -> BulkActionResult:
        return await self._bulk_apply(resume_file_ids, user, lambda rid: self.delete(rid, user))

    async def bulk_archive(self, resume_file_ids: list[uuid.UUID], user: User) -> BulkActionResult:
        return await self._bulk_apply(resume_file_ids, user, lambda rid: self.archive(rid, user))

    async def bulk_restore(self, resume_file_ids: list[uuid.UUID], user: User) -> BulkActionResult:
        return await self._bulk_apply(resume_file_ids, user, lambda rid: self.restore(rid, user))

    async def bulk_update_pipeline_stage(
        self, resume_file_ids: list[uuid.UUID], pipeline_stage: PipelineStage, user: User
    ) -> BulkActionResult:
        return await self._bulk_apply(
            resume_file_ids,
            user,
            lambda rid: self.update_pipeline_stage(rid, pipeline_stage, user),
        )
