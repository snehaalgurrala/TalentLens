"""AssessmentDashboardService — recruiter-facing read-only aggregation over an
assessment session's recordings/transcripts/analyses/communication assessment.

No AI, no scoring: this composes existing repository reads (several of which,
like AssessmentRecordingRepository.list_by_session, already existed but were
never wired to a route) into the shapes the recruiter dashboard needs. Same
org-scoped access model as AssessmentSessionService — every call is made by a
recruiter/org-admin/super-admin on a candidate's behalf.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.ai.communication.config import (
    get_listen_repeat_reference_sentence,
    get_read_aloud_reference_sentence,
)
from app.models.assessment_recording import RecordingStatus, RecordingType
from app.models.assessment_session import AssessmentSection, AssessmentSessionStatus
from app.schemas.assessment_analysis import AssessmentAnalysisResponse
from app.schemas.assessment_dashboard import (
    AssessmentRecordingDetail,
    AssessmentSessionCampaignInfo,
    AssessmentSessionCandidateInfo,
    AssessmentSessionFullResponse,
    AssessmentSessionListItem,
    AssessmentSessionListResponse,
)
from app.schemas.assessment_session import AssessmentRecordingResponse, AssessmentSessionResponse
from app.schemas.assessment_transcript import AssessmentTranscriptResponse
from app.schemas.communication_assessment import CommunicationAssessmentResponse

if TYPE_CHECKING:
    from app.models.assessment_recording import AssessmentRecording
    from app.models.assessment_session import AssessmentSession
    from app.models.user import User
    from app.repositories.assessment_analysis import AssessmentAnalysisRepository
    from app.repositories.assessment_recording import AssessmentRecordingRepository
    from app.repositories.assessment_session import AssessmentSessionRepository
    from app.repositories.assessment_transcript import AssessmentTranscriptRepository
    from app.repositories.campaign import CampaignRepository
    from app.repositories.candidate import CandidateRepository
    from app.repositories.communication_assessment import CommunicationAssessmentRepository
    from app.repositories.resume_file import ResumeFileRepository

_REFERENCE_SENTENCE_BY_TYPE = {
    RecordingType.READ_ALOUD: get_read_aloud_reference_sentence,
    RecordingType.LISTEN_REPEAT: get_listen_repeat_reference_sentence,
}

# Fixed 3-stage flow (mirrors AssessmentSessionService/the candidate-runner):
# used only to render a rough progress percentage on the sessions list.
_SECTION_ORDER = [
    AssessmentSection.APTITUDE,
    AssessmentSection.READ_ALOUD,
    AssessmentSection.LISTEN_REPEAT,
]


def _progress_percent(assessment_session: AssessmentSession) -> int:
    if assessment_session.status == AssessmentSessionStatus.COMPLETED:
        return 100
    index = _SECTION_ORDER.index(assessment_session.current_section)
    return round((index / len(_SECTION_ORDER)) * 100)


class AssessmentDashboardService:
    def __init__(
        self,
        session_repo: AssessmentSessionRepository,
        recording_repo: AssessmentRecordingRepository,
        transcript_repo: AssessmentTranscriptRepository,
        analysis_repo: AssessmentAnalysisRepository,
        communication_assessment_repo: CommunicationAssessmentRepository,
        campaign_repo: CampaignRepository,
        candidate_repo: CandidateRepository,
        resume_file_repo: ResumeFileRepository,
    ) -> None:
        self.session_repo = session_repo
        self.recording_repo = recording_repo
        self.transcript_repo = transcript_repo
        self.analysis_repo = analysis_repo
        self.communication_assessment_repo = communication_assessment_repo
        self.campaign_repo = campaign_repo
        self.candidate_repo = candidate_repo
        self.resume_file_repo = resume_file_repo

    def _require_org(self, user: User) -> uuid.UUID:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to view assessment results.",
            )
        return user.org_id

    async def _get_session(self, session_id: uuid.UUID, user: User) -> AssessmentSession:
        org_id = self._require_org(user)
        assessment_session = await self.session_repo.get_by_id(session_id, org_id)
        if assessment_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Assessment session not found."
            )
        return assessment_session

    async def get_full(self, session_id: uuid.UUID, user: User) -> AssessmentSessionFullResponse:
        assessment_session = await self._get_session(session_id, user)
        org_id = self._require_org(user)

        campaign = await self.campaign_repo.get_by_id(assessment_session.campaign_id, org_id)
        candidate = await self.candidate_repo.get_by_id_and_org(
            assessment_session.candidate_id, org_id
        )
        if campaign is None or candidate is None:
            # FKs cascade-delete together with the session, so reaching here
            # means unexpected data loss rather than a normal dashboard view.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Assessment session not found."
            )

        recordings = await self.recording_repo.list_by_session(assessment_session.id)

        recording_details: list[AssessmentRecordingDetail] = []
        for recording in recordings:
            transcript = await self.transcript_repo.get_by_recording_id(recording.id)
            analysis = None
            if transcript is not None:
                analysis = await self.analysis_repo.get_by_transcript_id(transcript.id)

            recording_details.append(
                AssessmentRecordingDetail(
                    recording=AssessmentRecordingResponse.model_validate(recording),
                    reference_sentence=_REFERENCE_SENTENCE_BY_TYPE[recording.recording_type](),
                    transcript=(
                        AssessmentTranscriptResponse.model_validate(transcript)
                        if transcript is not None
                        else None
                    ),
                    analysis=(
                        AssessmentAnalysisResponse.model_validate(analysis)
                        if analysis is not None
                        else None
                    ),
                )
            )

        communication_assessment = await self.communication_assessment_repo.get_by_session_id(
            assessment_session.id
        )
        resume_file = await self.resume_file_repo.get_by_candidate_and_campaign(
            assessment_session.candidate_id, assessment_session.campaign_id
        )

        return AssessmentSessionFullResponse(
            session=AssessmentSessionResponse.model_validate(assessment_session),
            candidate=AssessmentSessionCandidateInfo(
                id=candidate.id,
                first_name=candidate.first_name,
                last_name=candidate.last_name,
                email=candidate.email,
            ),
            campaign=AssessmentSessionCampaignInfo(id=campaign.id, title=campaign.title),
            pipeline_stage=resume_file.pipeline_stage if resume_file is not None else None,
            recordings=recording_details,
            communication_assessment=(
                CommunicationAssessmentResponse.model_validate(communication_assessment)
                if communication_assessment is not None
                else None
            ),
        )

    async def list_sessions(
        self, user: User, campaign_id: uuid.UUID | None = None
    ) -> AssessmentSessionListResponse:
        org_id = self._require_org(user)
        sessions = await self.session_repo.list_by_org(org_id, campaign_id)

        comm_assessments = await self.communication_assessment_repo.list_by_session_ids(
            [s.id for s in sessions]
        )
        comm_by_session = {c.assessment_session_id: c for c in comm_assessments}

        items = [
            AssessmentSessionListItem(
                session_id=s.id,
                candidate=AssessmentSessionCandidateInfo(
                    id=s.candidate.id,
                    first_name=s.candidate.first_name,
                    last_name=s.candidate.last_name,
                    email=s.candidate.email,
                ),
                campaign=AssessmentSessionCampaignInfo(id=s.campaign.id, title=s.campaign.title),
                status=s.status,
                current_section=s.current_section,
                progress_percent=_progress_percent(s),
                started_at=s.started_at,
                completed_at=s.completed_at,
                overall_score=(
                    comm_by_session[s.id].overall_score if s.id in comm_by_session else None
                ),
                communication_status=(
                    comm_by_session[s.id].status if s.id in comm_by_session else None
                ),
            )
            for s in sessions
        ]
        return AssessmentSessionListResponse(items=items, total=len(items))

    async def get_recording_audio(
        self, session_id: uuid.UUID, recording_type: RecordingType, user: User
    ) -> AssessmentRecording:
        assessment_session = await self._get_session(session_id, user)
        recording = await self.recording_repo.get_by_session_and_type(
            assessment_session.id, recording_type
        )
        if recording is None or recording.status != RecordingStatus.UPLOADED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found."
            )
        return recording

    async def get_session_by_candidate(
        self, candidate_id: uuid.UUID, campaign_id: uuid.UUID, user: User
    ) -> AssessmentSession:
        org_id = self._require_org(user)

        campaign = await self.campaign_repo.get_by_id(campaign_id, org_id)
        if campaign is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")

        candidate = await self.candidate_repo.get_by_id_and_org(candidate_id, org_id)
        if candidate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")

        assessment_session = await self.session_repo.get_by_campaign_and_candidate(
            campaign_id, candidate_id, org_id
        )
        if assessment_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No assessment session found for this candidate in this campaign.",
            )
        return assessment_session
