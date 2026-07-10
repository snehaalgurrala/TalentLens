from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DBSession
from app.repositories.notification_preference import NotificationPreferenceRepository
from app.schemas.notification_preference import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
)
from app.services.notification_preference import NotificationPreferenceService

router = APIRouter()


def get_notification_preference_service(db: DBSession) -> NotificationPreferenceService:
    return NotificationPreferenceService(NotificationPreferenceRepository(db))


NotificationPreferenceServiceDep = Annotated[
    NotificationPreferenceService, Depends(get_notification_preference_service)
]


@router.get(
    "/me",
    response_model=NotificationPreferenceResponse,
    summary="Get the current user's notification preferences",
)
async def get_my_notification_preferences(
    service: NotificationPreferenceServiceDep,
    current_user: CurrentUser,
) -> NotificationPreferenceResponse:
    row = await service.get_or_create(current_user.id)
    return NotificationPreferenceResponse.model_validate(row)


@router.patch(
    "/me",
    response_model=NotificationPreferenceResponse,
    summary="Update the current user's notification preferences",
)
async def update_my_notification_preferences(
    data: NotificationPreferenceUpdate,
    service: NotificationPreferenceServiceDep,
    current_user: CurrentUser,
) -> NotificationPreferenceResponse:
    row = await service.update(current_user.id, data)
    return NotificationPreferenceResponse.model_validate(row)
