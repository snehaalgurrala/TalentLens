import { useAuthActions } from "@/providers/auth-provider"
import { useAuthStore } from "@/store/auth-store"
import { useOrganizationStore } from "@/store/organization-store"
import { useUserStore } from "@/store/user-store"

/** Single entry point for auth session state + actions across the app. */
export function useAuth() {
  const { status } = useAuthStore()
  const { user } = useUserStore()
  const { organization } = useOrganizationStore()
  const { login, register, logout } = useAuthActions()

  return {
    user,
    organization,
    status,
    isAuthenticated: status === "authenticated",
    isInitializing: status === "idle" || status === "authenticating",
    login,
    register,
    logout,
  }
}
