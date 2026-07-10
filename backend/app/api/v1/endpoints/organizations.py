import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.api.deps import CurrentUser, DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.audit_log import AuditLogRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.organization_invitation import OrganizationInvitationRepository
from app.repositories.user import UserRepository
from app.schemas.organization import (
    InvitationCreate,
    InvitationResponse,
    OrganizationBootstrapRequest,
    OrganizationBootstrapResponse,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.schemas.user import UserResponse
from app.services.audit_log import AuditLogService
from app.services.email.email_service import EmailService
from app.services.email.smtp_provider import SMTPProvider
from app.services.organization import OrganizationService
from app.storage.factory import get_storage_backend

router = APIRouter()

_require_admin_role = RequireRoles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
AdminUser = Annotated[User, Depends(_require_admin_role)]


def get_organization_service(db: DBSession) -> OrganizationService:
    return OrganizationService(
        OrganizationRepository(db),
        UserRepository(db),
        OrganizationInvitationRepository(db),
        email_service=EmailService(SMTPProvider()),
        storage=get_storage_backend(),
        audit_service=AuditLogService(AuditLogRepository(db)),
    )


OrganizationServiceDep = Annotated[OrganizationService, Depends(get_organization_service)]


@router.post(
    "/bootstrap",
    response_model=OrganizationBootstrapResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new organization and its first ORG_ADMIN",
    responses={
        201: {"description": "Organization and admin account created."},
        409: {"description": "Organization slug or admin email already in use."},
        422: {"description": "Validation error."},
    },
)
async def bootstrap_organization(
    data: OrganizationBootstrapRequest,
    service: OrganizationServiceDep,
) -> OrganizationBootstrapResponse:
    organization, admin, tokens = await service.bootstrap(data)
    return OrganizationBootstrapResponse(
        organization=OrganizationResponse.model_validate(organization),
        admin=UserResponse.model_validate(admin),
        tokens=tokens,
    )


@router.post(
    "/{org_id}/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a recruiter to join an organization",
    responses={
        201: {"description": "Invitation created; raw token returned once."},
        403: {"description": "Insufficient role or not an admin of this organization."},
        404: {"description": "Organization not found."},
    },
)
async def invite_recruiter(
    org_id: uuid.UUID,
    data: InvitationCreate,
    service: OrganizationServiceDep,
    current_user: AdminUser,
) -> InvitationResponse:
    invitation, token = await service.invite(org_id, current_user, data)
    return InvitationResponse(
        id=invitation.id,
        org_id=invitation.org_id,
        email=invitation.email,
        status=invitation.status,
        expires_at=invitation.expires_at,
        token=token,
    )


@router.get(
    "/me",
    response_model=OrganizationResponse,
    summary="Get the current user's organization",
    responses={
        200: {"description": "The caller's organization."},
        404: {"description": "Organization not found."},
        422: {"description": "User has no organization."},
    },
)
async def get_my_organization(
    service: OrganizationServiceDep,
    current_user: CurrentUser,
) -> OrganizationResponse:
    org = await service.get_mine(current_user)
    return OrganizationResponse.model_validate(org)


@router.patch(
    "/me",
    response_model=OrganizationResponse,
    summary="Update the current user's organization profile",
    responses={
        200: {"description": "Updated organization."},
        403: {"description": "Only ORG_ADMIN/SUPER_ADMIN may update the organization."},
    },
)
async def update_my_organization(
    data: OrganizationUpdate,
    service: OrganizationServiceDep,
    current_user: AdminUser,
) -> OrganizationResponse:
    org = await service.update_mine(data, current_user)
    return OrganizationResponse.model_validate(org)


@router.post(
    "/me/logo",
    response_model=OrganizationResponse,
    summary="Upload the organization's logo",
    responses={
        200: {"description": "Logo uploaded; organization updated with the new logo_url."},
        403: {"description": "Only ORG_ADMIN/SUPER_ADMIN may update the organization."},
        422: {"description": "File too large or an unsupported image type."},
    },
)
async def upload_organization_logo(
    file: UploadFile,
    service: OrganizationServiceDep,
    current_user: AdminUser,
) -> OrganizationResponse:
    org = await service.upload_logo(file, current_user)
    return OrganizationResponse.model_validate(org)


@router.get(
    "/me/logo",
    summary="Download the organization's logo",
    responses={
        200: {"description": "Raw image bytes."},
        404: {"description": "No logo has been uploaded."},
    },
)
async def download_organization_logo(
    service: OrganizationServiceDep,
    current_user: CurrentUser,
) -> Response:
    org = await service.get_mine(current_user)
    if not org.logo_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No logo uploaded.")
    storage = get_storage_backend()
    data = await storage.load(org.logo_url)
    extension = org.logo_url.rsplit(".", 1)[-1].lower()
    media_type = {
        "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "svg": "image/svg+xml", "webp": "image/webp",
    }.get(extension, "application/octet-stream")
    return Response(content=data, media_type=media_type)
