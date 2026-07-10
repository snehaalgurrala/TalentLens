import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { platformAIConfigService } from "@/services/settings.service"
import type { ApiError, PlatformAIConfig, PlatformAIConfigUpdate } from "@/types"

export const platformAIConfigKeys = {
  all: ["platform-ai-config"] as const,
}

export function usePlatformAIConfig() {
  return useQuery<PlatformAIConfig, ApiError>({
    queryKey: platformAIConfigKeys.all,
    queryFn: platformAIConfigService.get,
  })
}

export function useUpdatePlatformAIConfig() {
  const queryClient = useQueryClient()
  return useMutation<PlatformAIConfig, ApiError, PlatformAIConfigUpdate>({
    mutationFn: (data) => platformAIConfigService.update(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: platformAIConfigKeys.all })
    },
  })
}
