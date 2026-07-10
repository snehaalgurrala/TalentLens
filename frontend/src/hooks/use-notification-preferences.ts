import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { notificationPreferenceService } from "@/services/settings.service"
import type { ApiError, NotificationPreference, NotificationPreferenceUpdate } from "@/types"

export const notificationPreferenceKeys = {
  all: ["notification-preferences"] as const,
}

export function useNotificationPreferences() {
  return useQuery<NotificationPreference, ApiError>({
    queryKey: notificationPreferenceKeys.all,
    queryFn: notificationPreferenceService.get,
  })
}

export function useUpdateNotificationPreferences() {
  const queryClient = useQueryClient()
  return useMutation<NotificationPreference, ApiError, NotificationPreferenceUpdate>({
    mutationFn: (data) => notificationPreferenceService.update(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: notificationPreferenceKeys.all })
    },
  })
}
