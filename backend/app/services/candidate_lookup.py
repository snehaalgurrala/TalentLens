"""
Shared candidate-id resolution used by every single-candidate service
(profile, notes, activity).

The candidate list hands back an id that is sometimes a real Candidate.id
and sometimes — when parsing hasn't produced a Candidate row yet — the
underlying ResumeFile.id used as a stand-in (see
CandidateManagementService._to_list_item). This resolves either form down
to the ResumeFile every mutation endpoint already keys on.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

if TYPE_CHECKING:
    from app.models.resume_file import ResumeFile
    from app.repositories.campaign import CampaignRepository
    from app.repositories.candidate import CandidateRepository
    from app.repositories.resume_file import ResumeFileRepository

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")


async def resolve_resume_file(
    id_: uuid.UUID,
    org_id: uuid.UUID,
    resume_file_repo: ResumeFileRepository,
    candidate_repo: CandidateRepository,
    campaign_repo: CampaignRepository,
) -> ResumeFile:
    rf = await resume_file_repo.get_by_id(id_)
    if rf is not None:
        campaign = await campaign_repo.get_by_id(rf.campaign_id, org_id)
        if campaign is None:
            raise _NOT_FOUND
        return rf

    candidate = await candidate_repo.get_by_id_and_org(id_, org_id)
    if candidate is None:
        raise _NOT_FOUND
    rf = await resume_file_repo.get_latest_by_candidate_id(candidate.id)
    if rf is None:
        raise _NOT_FOUND
    return rf
