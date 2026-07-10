import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User

# Fixed sentinel row ID — must match alembic/versions/c3d4e5f6a7b8_*.py.
PLATFORM_EMAIL_CONFIG_ID = uuid.UUID("00000000-0000-0000-0000-0000000000a2")


class EmailTestResult(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class PlatformEmailConfig(Base):
    """Platform-wide singleton (always exactly one row, at PLATFORM_EMAIL_CONFIG_ID).
    SUPER_ADMIN-editable. smtp_password is stored in plaintext — matching how
    it's stored in .env today (no worse), never returned by the API (see
    PlatformEmailConfigResponse.has_password)."""

    __tablename__ = "platform_email_configs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    smtp_host: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    smtp_port: Mapped[int] = mapped_column(Integer, nullable=False, default=587, server_default="587")
    smtp_username: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    smtp_password: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    smtp_from_email: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    smtp_from_name: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    smtp_tls: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    smtp_ssl: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_configured: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_test_status: Mapped[EmailTestResult | None] = mapped_column(
        Enum(EmailTestResult, name="emailtestresult"), nullable=True
    )
    last_test_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    updater: Mapped["User | None"] = relationship("User", lazy="raise")
