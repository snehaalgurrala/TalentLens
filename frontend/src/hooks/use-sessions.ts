import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { sessionService } from "@/services/settings.service"
import type { ApiError, UserSession } from "@/types"

export const sessionKeys = {
  all: ["sessions"] as const,
}

export function useSessions() {
  return useQuery<UserSession[], ApiError>({
    queryKey: sessionKeys.all,
    queryFn: sessionService.listMine,
  })
}

export function useRevokeSession() {
  const queryClient = useQueryClient()
  return useMutation<void, ApiError, string>({
    mutationFn: (sessionId) => sessionService.revoke(sessionId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: sessionKeys.all })
    },
  })
}

export function useRevokeOtherSessions() {
  const queryClient = useQueryClient()
  return useMutation<void, ApiError, void>({
    mutationFn: () => sessionService.revokeOthers(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: sessionKeys.all })
    },
  })
}
