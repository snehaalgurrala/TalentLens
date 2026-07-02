import type { TokenResponse } from "@/types/auth.types"
import type { User } from "@/types/user.types"

export interface Organization {
  id: string
  name: string
  slug: string
  is_active: boolean
  created_at: string
}

export interface OrganizationBootstrapRequest {
  org_name: string
  org_slug: string
  admin_email: string
  admin_password: string
  admin_full_name: string
}

export interface OrganizationBootstrapResponse {
  organization: Organization
  admin: User
  tokens: TokenResponse
}

export type InvitationStatus = "PENDING" | "ACCEPTED" | "EXPIRED" | "REVOKED"

export interface InvitationCreate {
  email: string
}

export interface Invitation {
  id: string
  org_id: string
  email: string
  status: InvitationStatus
  expires_at: string
  token: string
}
