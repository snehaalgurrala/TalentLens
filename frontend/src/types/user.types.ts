export type UserRole = "CANDIDATE" | "RECRUITER" | "ORG_ADMIN" | "SUPER_ADMIN"

export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
  org_id: string | null
  is_active: boolean
  created_at: string
}

/** Minimal user shape for assignment dropdowns and embedded references (e.g. a campaign's hiring manager). */
export interface UserSummary {
  id: string
  full_name: string
  email: string
  role: UserRole
}

export interface UserProfileUpdate {
  full_name?: string
}

export interface ChangePasswordRequest {
  current_password: string
  new_password: string
}

/** Row shape for the Settings > Users admin table (GET /users). */
export interface UserListItem {
  id: string
  full_name: string
  email: string
  role: UserRole
  is_active: boolean
  created_at: string
}
