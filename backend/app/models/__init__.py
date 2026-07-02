# Re-export all models so Alembic's env.py discovers them via `import app.models`.
from app.models.campaign import (  # noqa: F401
    Campaign,
    CampaignPriority,
    CampaignStatus,
    EmploymentType,
)
from app.models.candidate import Candidate  # noqa: F401
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
