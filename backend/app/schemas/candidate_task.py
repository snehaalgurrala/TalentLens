from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.candidate_task import TaskPriority, TaskStatus
from app.schemas.user import UserSummaryResponse


class CandidateTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resume_file_id: UUID
    title: str
    description: str | None
    due_date: datetime | None
    priority: TaskPriority
    status: TaskStatus
    assignee: UserSummaryResponse | None
    created_by: UserSummaryResponse | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CandidateTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)
    due_date: datetime | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: UUID | None = None


class CandidateTaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)
    due_date: datetime | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None


class CandidateTaskReassign(BaseModel):
    assignee_id: UUID | None = None
