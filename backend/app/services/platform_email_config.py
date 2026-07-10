import logging
from datetime import UTC, datetime

from app.models.platform_email_config import EmailTestResult, PlatformEmailConfig
from app.models.user import User
from app.repositories.platform_email_config import PlatformEmailConfigRepository
from app.schemas.platform_email_config import (
    PlatformEmailConfigResponse,
    PlatformEmailConfigUpdate,
    SendTestEmailResponse,
)
from app.services.audit_log import AuditLogService
from app.services.email.email_service import EmailService
from app.services.email.smtp_provider import SMTPConnectionConfig, SMTPProvider

logger = logging.getLogger(__name__)


def build_smtp_provider(config: PlatformEmailConfig) -> SMTPProvider:
    """The factory used by both real sends and admin-triggered test sends —
    always builds from the *current* DB config, not app.core.config.settings."""
    return SMTPProvider(
        SMTPConnectionConfig(
            host=config.smtp_host,
            port=config.smtp_port,
            username=config.smtp_username,
            password=config.smtp_password,
            from_email=config.smtp_from_email,
            from_name=config.smtp_from_name,
            tls=config.smtp_tls,
            ssl=config.smtp_ssl,
        )
    )


class PlatformEmailConfigService:
    def __init__(
        self, repo: PlatformEmailConfigRepository, audit_service: AuditLogService | None = None
    ) -> None:
        self.repo = repo
        self.audit_service = audit_service

    def _to_response(self, row: PlatformEmailConfig) -> PlatformEmailConfigResponse:
        return PlatformEmailConfigResponse(
            id=row.id,
            smtp_host=row.smtp_host,
            smtp_port=row.smtp_port,
            smtp_username=row.smtp_username,
            smtp_from_email=row.smtp_from_email,
            smtp_from_name=row.smtp_from_name,
            smtp_tls=row.smtp_tls,
            smtp_ssl=row.smtp_ssl,
            is_configured=row.is_configured,
            has_password=bool(row.smtp_password),
            last_test_at=row.last_test_at,
            last_test_status=row.last_test_status,
            last_test_error=row.last_test_error,
            updated_by=row.updated_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get(self) -> PlatformEmailConfigResponse:
        row = await self.repo.get()
        return self._to_response(row)

    async def update(
        self, data: PlatformEmailConfigUpdate, user: User
    ) -> PlatformEmailConfigResponse:
        row = await self.repo.get()
        updates = data.model_dump(exclude_unset=True)
        if updates:
            row = await self.repo.update(row, **updates, updated_by=user.id)
            if row.smtp_host and row.smtp_from_email:
                row = await self.repo.update(row, is_configured=True)
            if self.audit_service is not None:
                await self.audit_service.record(
                    org_id=None,
                    actor_id=user.id,
                    action="platform_email_config.updated",
                    entity_type="platform_email_config",
                    entity_id=row.id,
                    metadata={"fields": [k for k in updates if k != "smtp_password"]},
                )
        return self._to_response(row)

    async def send_test_email(self, to_email: str, user: User) -> SendTestEmailResponse:
        row = await self.repo.get()
        provider = build_smtp_provider(row)
        email_service = EmailService(provider)
        try:
            await email_service.send_test_email(to_email=to_email)
        except Exception as exc:
            logger.warning("Test email send failed", extra={"error": str(exc)}, exc_info=True)
            await self.repo.update(
                row,
                last_test_at=datetime.now(UTC),
                last_test_status=EmailTestResult.FAILURE,
                last_test_error=str(exc),
            )
            return SendTestEmailResponse(success=False, error=str(exc))

        await self.repo.update(
            row,
            last_test_at=datetime.now(UTC),
            last_test_status=EmailTestResult.SUCCESS,
            last_test_error=None,
        )
        return SendTestEmailResponse(success=True)
