import { api } from "@/services/api"
import type {
  Invitation,
  InvitationCreate,
  OrganizationBootstrapRequest,
  OrganizationBootstrapResponse,
  UserSummary,
} from "@/types"

export const organizationService = {
  bootstrap: (data: OrganizationBootstrapRequest) =>
    api.post<OrganizationBootstrapResponse>("/organizations/bootstrap", data),
  inviteRecruiter: (orgId: string, data: InvitationCreate) =>
    api.post<Invitation>(`/organizations/${orgId}/invitations`, data),
  /** Active ORG_ADMIN/RECRUITER accounts in the caller's org — for hiring manager / recruiter pickers. */
  listMembers: () => api.get<UserSummary[]>("/users/org-members"),
}
