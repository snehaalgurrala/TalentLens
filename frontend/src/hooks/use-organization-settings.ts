import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { organizationService } from "@/services/organization.service"
import { useOrganizationStore } from "@/store/organization-store"
import type { ApiError, Organization, OrganizationUpdate } from "@/types"

export const organizationSettingsKeys = {
  all: ["organization-settings"] as const,
  mine: () => [...organizationSettingsKeys.all, "mine"] as const,
  logo: () => [...organizationSettingsKeys.all, "logo"] as const,
}

/** Real GET /organizations/me fetch — closes the gap in use-organization.ts,
 * which only reads from the store. Also seeds the store on success so other
 * consumers of useOrganization() see real data too. */
export function useOrganizationSettings() {
  const { setOrganization } = useOrganizationStore()
  return useQuery<Organization, ApiError>({
    queryKey: organizationSettingsKeys.mine(),
    queryFn: async () => {
      const org = await organizationService.getMine()
      setOrganization(org)
      return org
    },
  })
}

export function useUpdateOrganization() {
  const queryClient = useQueryClient()
  const { setOrganization } = useOrganizationStore()
  return useMutation<Organization, ApiError, OrganizationUpdate>({
    mutationFn: (data) => organizationService.updateMine(data),
    onSuccess: (org) => {
      setOrganization(org)
      void queryClient.invalidateQueries({ queryKey: organizationSettingsKeys.all })
    },
  })
}

export function useUploadOrganizationLogo() {
  const queryClient = useQueryClient()
  const { setOrganization } = useOrganizationStore()
  return useMutation<Organization, ApiError, File>({
    mutationFn: (file) => organizationService.uploadLogo(file),
    onSuccess: (org) => {
      setOrganization(org)
      void queryClient.invalidateQueries({ queryKey: organizationSettingsKeys.all })
    },
  })
}
