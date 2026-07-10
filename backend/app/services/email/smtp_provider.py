"""SMTPProvider — the default EmailProvider implementation, delivering mail
via a standard SMTP server using stdlib smtplib.

smtplib is blocking; the project has no async SMTP dependency (aiosmtplib is
not in requirements.txt), so the send is pushed onto a worker thread via
asyncio.to_thread rather than adding a new dependency for a single call site.

SMTP connection fields are passed via the constructor (sourced from the
DB-backed PlatformEmailConfig singleton, see app.services.platform_email_config)
rather than read from app.core.config.settings directly — this lets a
one-off "send test email" call use whatever config is currently being
edited, not just the last-deployed env values.
"""

from __future__ import annotations

import asyncio
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings
from app.services.email.email_service import EmailProvider


@dataclass(frozen=True)
class SMTPConnectionConfig:
    host: str
    port: int
    username: str
    password: str
    from_email: str
    from_name: str
    tls: bool
    ssl: bool


def smtp_config_from_settings() -> SMTPConnectionConfig:
    """Fallback used only where no PlatformEmailConfig row can be loaded
    (e.g. a script running outside a DB session)."""
    return SMTPConnectionConfig(
        host=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USERNAME,
        password=settings.SMTP_PASSWORD,
        from_email=settings.SMTP_FROM_EMAIL,
        from_name=settings.SMTP_FROM_NAME,
        tls=settings.SMTP_TLS,
        ssl=settings.SMTP_SSL,
    )


class SMTPProvider(EmailProvider):
    def __init__(self, config: SMTPConnectionConfig | None = None) -> None:
        # Stored as given (possibly None), not resolved yet — SMTPProvider()
        # with no explicit config re-reads app.core.config.settings at each
        # send, matching the pre-refactor behavior (and letting tests/
        # scripts monkeypatch settings after construction). An explicit
        # config (built from the DB-backed PlatformEmailConfig singleton,
        # see app.services.platform_email_config) is snapshotted as-is.
        self._explicit_config = config

    @property
    def config(self) -> SMTPConnectionConfig:
        return self._explicit_config or smtp_config_from_settings()

    async def send(
        self, *, to_email: str, subject: str, html_body: str, text_body: str
    ) -> None:
        config = self.config
        message = self._build_message(config, to_email, subject, html_body, text_body)
        await asyncio.to_thread(self._send_sync, config, to_email, message)

    def _build_message(
        self,
        config: SMTPConnectionConfig,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> MIMEMultipart:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{config.from_name} <{config.from_email}>"
        message["To"] = to_email
        # Plain-text part first: per RFC 2046, the alternative parts of a
        # multipart/alternative message must be ordered least-to-most
        # faithful, so the HTML part must come last.
        message.attach(MIMEText(text_body, "plain"))
        message.attach(MIMEText(html_body, "html"))
        return message

    def _send_sync(
        self, config: SMTPConnectionConfig, to_email: str, message: MIMEMultipart
    ) -> None:
        smtp_cls = smtplib.SMTP_SSL if config.ssl else smtplib.SMTP
        with smtp_cls(config.host, config.port, timeout=10) as client:
            if config.tls and not config.ssl:
                client.starttls()
            if config.username and config.password:
                client.login(config.username, config.password)
            client.sendmail(config.from_email, [to_email], message.as_string())
