"""EmailService — renders the assessment-invitation templates and delegates
delivery to an injected EmailProvider.

EmailProvider is the seam that lets the transport be swapped later (SendGrid,
SES, Azure Communication Services, ...) without touching
AssessmentInvitationService: only app/services/email/smtp_provider.py (or a
new sibling module implementing EmailProvider) would change.
"""

from __future__ import annotations

import abc
from pathlib import Path
from string import Template

_TEMPLATES_DIR = Path(__file__).parent / "templates"


class EmailProvider(abc.ABC):
    """Abstraction over the underlying email transport."""

    @abc.abstractmethod
    async def send(
        self, *, to_email: str, subject: str, html_body: str, text_body: str
    ) -> None: ...


class EmailService:
    def __init__(self, provider: EmailProvider) -> None:
        self.provider = provider

    def _render(self, template_name: str, **context: str) -> str:
        template_path = _TEMPLATES_DIR / template_name
        template = Template(template_path.read_text(encoding="utf-8"))
        return template.substitute(**context)

    async def send_assessment_invitation(
        self,
        *,
        to_email: str,
        candidate_name: str,
        campaign_name: str,
        assessment_url: str,
        expires_at_display: str,
        duration_display: str,
    ) -> None:
        context = {
            "candidate_name": candidate_name,
            "campaign_name": campaign_name,
            "assessment_url": assessment_url,
            "expires_at": expires_at_display,
            "duration": duration_display,
        }
        html_body = self._render("assessment_invitation.html", **context)
        text_body = self._render("assessment_invitation.txt", **context)
        await self.provider.send(
            to_email=to_email,
            subject="TalentLens Assessment Invitation",
            html_body=html_body,
            text_body=text_body,
        )

    async def send_organization_invitation(
        self,
        *,
        to_email: str,
        org_name: str,
        inviter_name: str,
        registration_url: str,
        expires_at_display: str,
    ) -> None:
        context = {
            "org_name": org_name,
            "inviter_name": inviter_name,
            "registration_url": registration_url,
            "expires_at": expires_at_display,
        }
        html_body = self._render("organization_invitation.html", **context)
        text_body = self._render("organization_invitation.txt", **context)
        await self.provider.send(
            to_email=to_email,
            subject=f"You're invited to join {org_name} on TalentLens",
            html_body=html_body,
            text_body=text_body,
        )

    async def send_test_email(self, *, to_email: str) -> None:
        html_body = self._render("test_email.html")
        text_body = self._render("test_email.txt")
        await self.provider.send(
            to_email=to_email,
            subject="TalentLens Test Email",
            html_body=html_body,
            text_body=text_body,
        )
