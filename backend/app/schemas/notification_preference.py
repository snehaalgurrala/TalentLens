from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationPreferenceUpdate(BaseModel):
    assessment_completed: bool | None = None
    assessment_started: bool | None = None
    invitation_sent: bool | None = None
    invitation_opened: bool | None = None
    candidate_shortlisted: bool | None = None
    ai_ranking_completed: bool | None = None
    daily_summary: bool | None = None
    weekly_summary: bool | None = None
    email_enabled: bool | None = None
    in_app_enabled: bool | None = None


class NotificationPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    assessment_completed: bool
    assessment_started: bool
    invitation_sent: bool
    invitation_opened: bool
    candidate_shortlisted: bool
    ai_ranking_completed: bool
    daily_summary: bool
    weekly_summary: bool
    email_enabled: bool
    in_app_enabled: bool
    created_at: datetime
    updated_at: datetime
