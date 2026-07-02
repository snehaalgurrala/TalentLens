"use client"

import type * as React from "react"

import { useAuth } from "@/hooks/use-auth"
import { usePermissions } from "@/hooks/use-permissions"
import type { Permission } from "@/config/permissions"
import type { UserRole } from "@/types"

interface GuardProps {
  children: React.ReactNode
  fallback?: React.ReactNode
}

/** Renders `children` only for an authenticated user. UI-level only — route protection is handled by middleware + `ProtectedShell`. */
function AuthGuard({ children, fallback = null }: GuardProps) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <>{children}</> : <>{fallback}</>
}

interface RoleGuardProps extends GuardProps {
  roles: UserRole[]
}

/** Renders `children` only if the current user's role is in `roles`. */
function RoleGuard({ roles, children, fallback = null }: RoleGuardProps) {
  const { hasAnyRole } = usePermissions()
  return hasAnyRole(...roles) ? <>{children}</> : <>{fallback}</>
}

interface PermissionGuardProps extends GuardProps {
  permission: Permission
}

/** Renders `children` only if the current user's role grants `permission`. */
function PermissionGuard({ permission, children, fallback = null }: PermissionGuardProps) {
  const { hasPermission } = usePermissions()
  return hasPermission(permission) ? <>{children}</> : <>{fallback}</>
}

export { AuthGuard, RoleGuard, PermissionGuard }
