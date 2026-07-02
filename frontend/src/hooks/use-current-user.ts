import { useAuthStore } from "@/store/auth-store"
import { useUserStore } from "@/store/user-store"

/** The authenticated user's profile, plus whether the session is still bootstrapping. */
export function useCurrentUser() {
  const { user } = useUserStore()
  const { status } = useAuthStore()

  return {
    user,
    isLoading: status === "idle" || status === "authenticating",
  }
}
