import { ROLE_PERMISSIONS, type Permission } from "@/config/permissions"
import type { UserRole } from "@/types"
import { useUserStore } from "@/store/user-store"

/** Role-derived permission checks. See `config/permissions.ts` for the matrix. */
export function usePermissions() {
  const { user } = useUserStore()
  const role = user?.role ?? null
  const permissions = role ? ROLE_PERMISSIONS[role] : []

  function hasPermission(permission: Permission): boolean {
    return permissions.includes(permission)
  }

  function hasAnyRole(...roles: UserRole[]): boolean {
    return role !== null && roles.includes(role)
  }

  return { role, permissions, hasPermission, hasAnyRole }
}
