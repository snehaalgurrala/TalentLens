import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { platformEmailConfigService } from "@/services/settings.service"
import type {
  ApiError,
  PlatformEmailConfig,
  PlatformEmailConfigUpdate,
  SendTestEmailResponse,
} from "@/types"

export const platformEmailConfigKeys = {
  all: ["platform-email-config"] as const,
}

export function usePlatformEmailConfig() {
  return useQuery<PlatformEmailConfig, ApiError>({
    queryKey: platformEmailConfigKeys.all,
    queryFn: platformEmailConfigService.get,
  })
}

export function useUpdatePlatformEmailConfig() {
  const queryClient = useQueryClient()
  return useMutation<PlatformEmailConfig, ApiError, PlatformEmailConfigUpdate>({
    mutationFn: (data) => platformEmailConfigService.update(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: platformEmailConfigKeys.all })
    },
  })
}

export function useSendTestEmail() {
  const queryClient = useQueryClient()
  return useMutation<SendTestEmailResponse, ApiError, string>({
    mutationFn: (toEmail) => platformEmailConfigService.sendTest(toEmail),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: platformEmailConfigKeys.all })
    },
  })
}
