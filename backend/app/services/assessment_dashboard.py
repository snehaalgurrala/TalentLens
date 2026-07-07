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
from app.schemas.assessment_analysis import AssessmentAnalysisResponse
from app.schemas.assessment_dashboard import AssessmentRecordingDetail, AssessmentSessionFullResponse
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

_REFERENCE_SENTENCE_BY_TYPE = {
    RecordingType.READ_ALOUD: get_read_aloud_reference_sentence,
    RecordingType.LISTEN_REPEAT: get_listen_repeat_reference_sentence,
}


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
    ) -> None:
        self.session_repo = session_repo
        self.recording_repo = recording_repo
        self.transcript_repo = transcript_repo
        self.analysis_repo = analysis_repo
        self.communication_assessment_repo = communication_assessment_repo
        self.campaign_repo = campaign_repo
        self.candidate_repo = candidate_repo

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

        return AssessmentSessionFullResponse(
            session=AssessmentSessionResponse.model_validate(assessment_session),
            recordings=recording_details,
            communication_assessment=(
                CommunicationAssessmentResponse.model_validate(communication_assessment)
                if communication_assessment is not None
                else None
            ),
        )

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
