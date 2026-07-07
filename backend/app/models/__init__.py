# Re-export all models so Alembic's env.py discovers them via `import app.models`.
from app.models.assessment_analysis import (  # noqa: F401
    AnalysisStatus,
    AnalysisType,
    AssessmentAnalysis,
)
from app.models.assessment_answer import AssessmentAnswer  # noqa: F401
from app.models.assessment_recording import (  # noqa: F401
    AssessmentRecording,
    RecordingStatus,
    RecordingType,
)
from app.models.assessment_session import (  # noqa: F401
    AssessmentSection,
    AssessmentSession,
    AssessmentSessionStatus,
)
from app.models.assessment_transcript import (  # noqa: F401
    AssessmentTranscript,
    TranscriptStatus,
)
from app.models.campaign import (  # noqa: F401
    Campaign,
    CampaignPriority,
    CampaignStatus,
    EmploymentType,
)
from app.models.candidate import Candidate  # noqa: F401
from app.models.candidate_activity import ActivityEventType, CandidateActivity  # noqa: F401
from app.models.candidate_note import CandidateNote  # noqa: F401
from app.models.candidate_task import CandidateTask, TaskPriority, TaskStatus  # noqa: F401
from app.models.embedding import EmbeddingStatus  # noqa: F401
from app.models.job_description import JobDescription, ParsingStatus  # noqa: F401
from app.models.organization import Organization  # noqa: F401
from app.models.organization_invitation import (  # noqa: F401
    InvitationStatus,
    OrganizationInvitation,
)
from app.models.parsed_resume import ParsedResume  # noqa: F401
from app.models.resume_file import ResumeFile, ReviewStatus, UploadStatus  # noqa: F401
from app.models.scoring_rule import ScoringRule  # noqa: F401
from app.models.user import User, UserRole  # noqa: F401
