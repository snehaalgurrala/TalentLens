import { useOrganizationStore } from "@/store/organization-store"
import { useUserStore } from "@/store/user-store"

/**
 * `organization` (name, slug, etc.) is only ever populated once something
 * calls `setOrganization` — there is no `GET /organizations/{id}` endpoint
 * on the backend yet, so today this always resolves to `null`. `orgId` comes
 * straight from the user and is reliable now.
 */
export function useOrganization() {
  const { organization } = useOrganizationStore()
  const { user } = useUserStore()

  return {
    organization,
    orgId: user?.org_id ?? null,
    isLoading: false,
  }
}
