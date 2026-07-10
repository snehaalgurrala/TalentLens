import { useQuery } from "@tanstack/react-query"

import { billingService } from "@/services/settings.service"
import type { ApiError, BillingUsage } from "@/types"

export const billingKeys = {
  usage: ["billing", "usage"] as const,
}

export function useBillingUsage() {
  return useQuery<BillingUsage, ApiError>({
    queryKey: billingKeys.usage,
    queryFn: billingService.getUsage,
  })
}
