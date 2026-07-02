import type { UserRole } from "@/types"

/**
 * The backend only exposes `role` on the user, not granular permissions.
 * This matrix is a frontend-only derivation — revisit if the backend ever
 * grows a real permissions endpoint.
 */
export const PERMISSIONS = {
  MANAGE_ORGANIZATION: "organization:manage",
  MANAGE_USERS: "users:manage",
  INVITE_RECRUITERS: "recruiters:invite",
  MANAGE_CAMPAIGNS: "campaigns:manage",
  MANAGE_CANDIDATES: "candidates:manage",
  VIEW_ANALYTICS: "analytics:view",
} as const

export type Permission = (typeof PERMISSIONS)[keyof typeof PERMISSIONS]

export const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  SUPER_ADMIN: [
    PERMISSIONS.MANAGE_ORGANIZATION,
    PERMISSIONS.MANAGE_USERS,
    PERMISSIONS.INVITE_RECRUITERS,
    PERMISSIONS.MANAGE_CAMPAIGNS,
    PERMISSIONS.MANAGE_CANDIDATES,
    PERMISSIONS.VIEW_ANALYTICS,
  ],
  ORG_ADMIN: [
    PERMISSIONS.MANAGE_USERS,
    PERMISSIONS.INVITE_RECRUITERS,
    PERMISSIONS.MANAGE_CAMPAIGNS,
    PERMISSIONS.MANAGE_CANDIDATES,
    PERMISSIONS.VIEW_ANALYTICS,
  ],
  RECRUITER: [
    PERMISSIONS.MANAGE_CAMPAIGNS,
    PERMISSIONS.MANAGE_CANDIDATES,
    PERMISSIONS.VIEW_ANALYTICS,
  ],
  CANDIDATE: [],
}

/** Human-readable label for a backend role, used in profile menus and badges. */
export const ROLE_LABELS: Record<UserRole, string> = {
  SUPER_ADMIN: "Super Admin",
  ORG_ADMIN: "Org Admin",
  RECRUITER: "Recruiter",
  CANDIDATE: "Candidate",
}
