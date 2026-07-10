import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.notification import Notification, NotificationType
from app.services.notification import NotificationService, notification_channel


def make_notification(**overrides) -> Notification:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        type=NotificationType.SUCCESS,
        title="Assessment Completed",
        message="Jane Doe completed their communication assessment for Data Scientist.",
        resume_file_id=uuid.uuid4(),
        is_read=False,
        created_at=now,
    )
    defaults.update(overrides)
    return Notification(**defaults)


class TestCreate:
    async def test_creates_row_and_publishes_it(self):
        notification = make_notification()
        repo = MagicMock()
        repo.create = AsyncMock(return_value=notification)
        service = NotificationService(repo)

        with patch("app.services.notification._publish", AsyncMock()) as mock_publish:
            result = await service.create(
                organization_id=notification.organization_id,
                user_id=notification.user_id,
                type=NotificationType.SUCCESS,
                title=notification.title,
                message=notification.message,
                resume_file_id=notification.resume_file_id,
            )

        assert result is notification
        repo.create.assert_awaited_once_with(
            organization_id=notification.organization_id,
            user_id=notification.user_id,
            type=NotificationType.SUCCESS,
            title=notification.title,
            message=notification.message,
            resume_file_id=notification.resume_file_id,
        )
        mock_publish.assert_awaited_once_with(notification.user_id, notification)

    async def test_publish_failure_does_not_fail_create(self):
        notification = make_notification()
        repo = MagicMock()
        repo.create = AsyncMock(return_value=notification)
        service = NotificationService(repo)

        with patch(
            "app.services.notification._publish", AsyncMock(side_effect=RuntimeError("redis down"))
        ):
            with pytest.raises(RuntimeError):
                await service.create(
                    organization_id=notification.organization_id,
                    user_id=notification.user_id,
                    type=NotificationType.SUCCESS,
                    title=notification.title,
                    message=notification.message,
                )


class TestListForUser:
    async def test_delegates_to_repo(self):
        user_id = uuid.uuid4()
        notifications = [make_notification(user_id=user_id)]
        repo = MagicMock()
        repo.list_by_user = AsyncMock(return_value=notifications)
        service = NotificationService(repo)

        result = await service.list_for_user(user_id)

        assert result == notifications
        repo.list_by_user.assert_awaited_once_with(user_id)


class TestMarkRead:
    async def test_marks_own_notification_read(self):
        notification = make_notification()
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=notification)
        repo.mark_read = AsyncMock(return_value=notification)
        service = NotificationService(repo)

        result = await service.mark_read(notification.id, notification.user_id)

        assert result is notification
        repo.mark_read.assert_awaited_once_with(notification)

    async def test_not_found_raises_404(self):
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=None)
        service = NotificationService(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.mark_read(uuid.uuid4(), uuid.uuid4())
        assert exc_info.value.status_code == 404

    async def test_belonging_to_another_user_raises_404(self):
        notification = make_notification()
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=notification)
        service = NotificationService(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.mark_read(notification.id, uuid.uuid4())
        assert exc_info.value.status_code == 404


class TestMarkAllRead:
    async def test_delegates_to_repo(self):
        user_id = uuid.uuid4()
        repo = MagicMock()
        repo.mark_all_read = AsyncMock(return_value=3)
        service = NotificationService(repo)

        result = await service.mark_all_read(user_id)

        assert result == 3
        repo.mark_all_read.assert_awaited_once_with(user_id)


class TestNotificationChannel:
    def test_includes_user_id(self):
        user_id = uuid.uuid4()
        assert notification_channel(user_id) == f"notifications:{user_id}"
