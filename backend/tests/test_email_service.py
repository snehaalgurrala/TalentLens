"""Unit tests for the email abstraction (app/services/email/):
  - EmailService renders both templates and delegates to the injected
    EmailProvider (SMTP mocked out entirely via a fake provider).
  - SMTPProvider is tested against a mocked smtplib.SMTP/SMTP_SSL — no real
    network connection is ever made.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import settings
from app.services.email.email_service import EmailProvider, EmailService
from app.services.email.smtp_provider import SMTPProvider


class _FakeProvider(EmailProvider):
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, *, to_email: str, subject: str, html_body: str, text_body: str) -> None:
        self.sent.append(
            {
                "to_email": to_email,
                "subject": subject,
                "html_body": html_body,
                "text_body": text_body,
            }
        )


class TestEmailServiceRendering:
    async def test_send_assessment_invitation_renders_placeholders(self):
        provider = _FakeProvider()
        service = EmailService(provider)

        await service.send_assessment_invitation(
            to_email="jane.doe@example.com",
            candidate_name="Jane Doe",
            campaign_name="Backend Engineer",
            assessment_url="https://app.talentlens.io/assessment/start/tok123",
            expires_at_display="July 10, 2026 at 12:00 UTC",
            duration_display="Approximately 20-30 minutes",
        )

        assert len(provider.sent) == 1
        message = provider.sent[0]
        assert message["to_email"] == "jane.doe@example.com"
        assert message["subject"] == "TalentLens Assessment Invitation"
        for body in (message["html_body"], message["text_body"]):
            assert "Jane Doe" in body
            assert "Backend Engineer" in body
            assert "https://app.talentlens.io/assessment/start/tok123" in body
            assert "July 10, 2026 at 12:00 UTC" in body
            assert "Approximately 20-30 minutes" in body
        # Templates must be fully substituted — no leftover $placeholders.
        assert "$" not in message["html_body"]
        assert "$" not in message["text_body"]

    async def test_provider_exception_propagates(self):
        provider = MagicMock()
        provider.send = AsyncMock(side_effect=RuntimeError("boom"))
        service = EmailService(provider)

        with pytest.raises(RuntimeError, match="boom"):
            await service.send_assessment_invitation(
                to_email="jane.doe@example.com",
                candidate_name="Jane Doe",
                campaign_name="Backend Engineer",
                assessment_url="https://app.talentlens.io/assessment/start/tok123",
                expires_at_display="July 10, 2026",
                duration_display="20-30 minutes",
            )


class TestSMTPProvider:
    def test_build_message_sets_headers_and_both_parts(self):
        provider = SMTPProvider()
        message = provider._build_message(
            provider.config, "candidate@example.com", "Subject line", "<p>html</p>", "text body"
        )

        assert message["To"] == "candidate@example.com"
        assert message["Subject"] == "Subject line"
        assert settings.SMTP_FROM_EMAIL in message["From"]
        parts = message.get_payload()
        assert len(parts) == 2
        assert parts[0].get_content_type() == "text/plain"
        assert parts[1].get_content_type() == "text/html"

    async def test_send_uses_starttls_and_login_when_configured(self):
        provider = SMTPProvider()
        fake_client = MagicMock()
        fake_client.__enter__ = MagicMock(return_value=fake_client)
        fake_client.__exit__ = MagicMock(return_value=False)

        with (
            patch("app.services.email.smtp_provider.settings.SMTP_TLS", True),
            patch("app.services.email.smtp_provider.settings.SMTP_SSL", False),
            patch("app.services.email.smtp_provider.settings.SMTP_USERNAME", "user"),
            patch("app.services.email.smtp_provider.settings.SMTP_PASSWORD", "pass"),
            patch("smtplib.SMTP", return_value=fake_client) as mock_smtp_cls,
        ):
            await provider.send(
                to_email="candidate@example.com",
                subject="Subj",
                html_body="<p>hi</p>",
                text_body="hi",
            )

        mock_smtp_cls.assert_called_once()
        fake_client.starttls.assert_called_once()
        fake_client.login.assert_called_once_with("user", "pass")
        fake_client.sendmail.assert_called_once()

    async def test_send_skips_login_when_no_credentials_configured(self):
        provider = SMTPProvider()
        fake_client = MagicMock()
        fake_client.__enter__ = MagicMock(return_value=fake_client)
        fake_client.__exit__ = MagicMock(return_value=False)

        with (
            patch("app.services.email.smtp_provider.settings.SMTP_TLS", False),
            patch("app.services.email.smtp_provider.settings.SMTP_SSL", False),
            patch("app.services.email.smtp_provider.settings.SMTP_USERNAME", ""),
            patch("app.services.email.smtp_provider.settings.SMTP_PASSWORD", ""),
            patch("smtplib.SMTP", return_value=fake_client),
        ):
            await provider.send(
                to_email="candidate@example.com",
                subject="Subj",
                html_body="<p>hi</p>",
                text_body="hi",
            )

        fake_client.starttls.assert_not_called()
        fake_client.login.assert_not_called()
        fake_client.sendmail.assert_called_once()
