"""Recruiter notification endpoints — list/mark-read/mark-all-read (plain
REST, matching frontend/src/services/notification.service.ts's existing
contract) plus a Server-Sent-Events stream so a connected browser gets a new
notification the instant NotificationService.create() publishes it, with no
client-side polling. See app.services.notification for the Redis Pub/Sub
bridge that makes this work across the FastAPI and Celery worker processes.
"""

import time
import uuid
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, DBSession
from app.core.redis import get_redis_client
from app.core.security import decode_token
from app.models.user import User
from app.repositories.notification import NotificationRepository
from app.repositories.user import UserRepository
from app.schemas.notification import NotificationResponse, NotificationUpdate
from app.services.notification import NotificationService, notification_channel

router = APIRouter()

# SSE keep-alive: EventSource has no built-in ping, and idle proxies/load
# balancers can silently drop a connection with no traffic for a while —
# this is a comment on an already-open stream, not a new request, so it
# does not count as the "no polling" the task rules out.
_KEEPALIVE_SECONDS = 20

# Recycle the connection periodically rather than holding it open forever:
# EventSource reconnects to the same URL automatically on a clean stream end
# (no error, just the generator returning), so this is invisible to the
# user, but it bounds how many of these a long-running FastAPI process can
# accumulate and lets a `--reload`/deploy restart drain connections instead
# of waiting on ones that would otherwise never close on their own.
_MAX_CONNECTION_SECONDS = 600


def get_notification_service(db: DBSession) -> NotificationService:
    return NotificationService(NotificationRepository(db))


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]


async def get_current_user_from_query_token(
    db: DBSession, token: Annotated[str | None, Query()] = None
) -> User:
    """EventSource cannot set an Authorization header, so the SSE stream
    authenticates via a `?token=` query param instead — same decode path as
    CurrentUser, just sourced differently. Mirrors the query/header
    dual-path already established for candidate uploads in
    assessment_sessions.resolve_recording_upload_org_id."""
    if token:
        try:
            payload = decode_token(token)
            if payload.get("type") == "access":
                user = await UserRepository(db).get_by_id(uuid.UUID(payload["sub"]))
                if user is not None and user.is_active:
                    return user
        except (jwt.InvalidTokenError, ValueError, KeyError):
            pass
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials."
    )


@router.get(
    "/",
    response_model=list[NotificationResponse],
    summary="List the current user's notifications (most recent first)",
)
async def list_notifications(
    service: NotificationServiceDep, current_user: CurrentUser
) -> list[NotificationResponse]:
    notifications = await service.list_for_user(current_user.id)
    return [NotificationResponse.model_validate(n) for n in notifications]


@router.patch(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Mark a notification read",
    responses={404: {"description": "Notification not found."}},
)
async def update_notification(
    notification_id: uuid.UUID,
    data: NotificationUpdate,
    service: NotificationServiceDep,
    current_user: CurrentUser,
) -> NotificationResponse:
    notification = await service.mark_read(notification_id, current_user.id)
    return NotificationResponse.model_validate(notification)


@router.post(
    "/mark-all-read",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark every notification for the current user as read",
)
async def mark_all_read(service: NotificationServiceDep, current_user: CurrentUser) -> None:
    await service.mark_all_read(current_user.id)


@router.get(
    "/stream",
    summary="Server-Sent-Events stream of new notifications for the current user",
)
async def stream_notifications(
    current_user: Annotated[User, Depends(get_current_user_from_query_token)],
) -> StreamingResponse:
    async def event_source():
        redis = get_redis_client()
        pubsub = redis.pubsub()
        await pubsub.subscribe(notification_channel(current_user.id))
        started = time.monotonic()
        try:
            while time.monotonic() - started < _MAX_CONNECTION_SECONDS:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=_KEEPALIVE_SECONDS
                )
                if message is None:
                    yield ": keep-alive\n\n"
                    continue
                yield f"data: {message['data']}\n\n"
        finally:
            await pubsub.unsubscribe(notification_channel(current_user.id))
            await pubsub.aclose()

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
