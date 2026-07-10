import type { UserRole } from "@/types"

/** Roles that can be assigned to an org member — SUPER_ADMIN can only be
 * granted by an existing SUPER_ADMIN (also enforced server-side). */
export function getAssignableRoles(callerRole: UserRole | null): UserRole[] {
  const base: UserRole[] = ["RECRUITER", "ORG_ADMIN"]
  return callerRole === "SUPER_ADMIN" ? [...base, "SUPER_ADMIN"] : base
}
