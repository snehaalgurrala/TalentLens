from app.models.platform_ai_config import PlatformAIConfig
from app.models.user import User
from app.repositories.platform_ai_config import PlatformAIConfigRepository
from app.schemas.platform_ai_config import PlatformAIConfigResponse, PlatformAIConfigUpdate
from app.services.audit_log import AuditLogService


class PlatformAIConfigService:
    """SUPER_ADMIN-only, platform-wide singleton. See PlatformAIConfig's
    docstring and the plan (Part A.5) for exactly which fields have a real
    runtime consumer vs. are persisted-but-not-yet-wired config."""

    def __init__(
        self, repo: PlatformAIConfigRepository, audit_service: AuditLogService | None = None
    ) -> None:
        self.repo = repo
        self.audit_service = audit_service

    async def get(self) -> PlatformAIConfig:
        return await self.repo.get()

    async def update(self, data: PlatformAIConfigUpdate, user: User) -> PlatformAIConfigResponse:
        row = await self.get()
        updates = data.model_dump(exclude_unset=True)
        embedding_model_changed = (
            "embedding_model" in updates and updates["embedding_model"] != row.embedding_model
        )
        if updates:
            row = await self.repo.update(row, **updates, updated_by=user.id)
            if self.audit_service is not None:
                await self.audit_service.record(
                    org_id=None,
                    actor_id=user.id,
                    action="platform_ai_config.updated",
                    entity_type="platform_ai_config",
                    entity_id=row.id,
                    metadata={"fields": list(updates.keys())},
                )
        response = PlatformAIConfigResponse.model_validate(row)
        # Changing embedding_model does not hot-reload the process-wide
        # singleton loaded once at FastAPI startup (see
        # local_embedding_service.preload_model) — surfaced honestly rather
        # than implying the change took effect immediately.
        response.restart_required = embedding_model_changed
        return response
