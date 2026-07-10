import { api } from "@/services/api"
import { apiClient } from "@/services/axios"
import type {
  Invitation,
  InvitationCreate,
  Organization,
  OrganizationBootstrapRequest,
  OrganizationBootstrapResponse,
  OrganizationUpdate,
  UserSummary,
} from "@/types"

export const organizationService = {
  bootstrap: (data: OrganizationBootstrapRequest) =>
    api.post<OrganizationBootstrapResponse>("/organizations/bootstrap", data),
  inviteRecruiter: (orgId: string, data: InvitationCreate) =>
    api.post<Invitation>(`/organizations/${orgId}/invitations`, data),
  /** Active ORG_ADMIN/RECRUITER accounts in the caller's org — for hiring manager / recruiter pickers. */
  listMembers: () => api.get<UserSummary[]>("/users/org-members"),
  getMine: () => api.get<Organization>("/organizations/me"),
  updateMine: (data: OrganizationUpdate) => api.patch<Organization>("/organizations/me", data),
  uploadLogo: async (file: File) => {
    const formData = new FormData()
    formData.append("file", file)
    const { data } = await apiClient.post<Organization>("/organizations/me/logo", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    return data
  },
  /** Fetches the org logo as a blob object URL (the download route is
   * authenticated, so a plain <img src="/api/..."> can't be used). */
  getLogoObjectUrl: async () => {
    const { data } = await apiClient.get("/organizations/me/logo", { responseType: "blob" })
    return URL.createObjectURL(data as Blob)
  },
}
