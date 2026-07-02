import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.organization import OrganizationRepository
from app.repositories.organization_invitation import OrganizationInvitationRepository
from app.repositories.user import UserRepository
from app.schemas.organization import (
    InvitationCreate,
    InvitationResponse,
    OrganizationBootstrapRequest,
    OrganizationBootstrapResponse,
    OrganizationResponse,
)
from app.schemas.user import UserResponse
from app.services.organization import OrganizationService

router = APIRouter()

_require_admin_role = RequireRoles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
AdminUser = Annotated[User, Depends(_require_admin_role)]


def get_organization_service(db: DBSession) -> OrganizationService:
    return OrganizationService(
        OrganizationRepository(db),
        UserRepository(db),
        OrganizationInvitationRepository(db),
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
