import { useQuery } from "@tanstack/react-query"

import { systemHealthService } from "@/services/settings.service"
import type { ApiError, SystemHealthResponse } from "@/types"

const REFETCH_INTERVAL_MS = 15_000

export const systemHealthKeys = {
  all: ["system-health"] as const,
}

export function useSystemHealth() {
  return useQuery<SystemHealthResponse, ApiError>({
    queryKey: systemHealthKeys.all,
    queryFn: systemHealthService.get,
    refetchInterval: REFETCH_INTERVAL_MS,
  })
}
