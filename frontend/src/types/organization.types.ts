import type { TokenResponse } from "@/types/auth.types"
import type { User } from "@/types/user.types"

export interface Organization {
  id: string
  name: string
  slug: string
  is_active: boolean
  logo_url: string | null
  industry: string | null
  website: string | null
  company_email: string | null
  phone: string | null
  address_line1: string | null
  address_line2: string | null
  city: string | null
  state: string | null
  postal_code: string | null
  country: string | null
  timezone: string
  description: string | null
  created_at: string
}

export interface OrganizationUpdate {
  name?: string
  industry?: string
  website?: string
  company_email?: string
  phone?: string
  address_line1?: string
  address_line2?: string
  city?: string
  state?: string
  postal_code?: string
  country?: string
  timezone?: string
  description?: string
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
