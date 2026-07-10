import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { recruitmentSettingsService } from "@/services/settings.service"
import type { ApiError, RecruitmentSettings, RecruitmentSettingsUpdate } from "@/types"

export const recruitmentSettingsKeys = {
  all: ["recruitment-settings"] as const,
}

export function useRecruitmentSettings() {
  return useQuery<RecruitmentSettings, ApiError>({
    queryKey: recruitmentSettingsKeys.all,
    queryFn: recruitmentSettingsService.get,
  })
}

export function useUpdateRecruitmentSettings() {
  const queryClient = useQueryClient()
  return useMutation<RecruitmentSettings, ApiError, RecruitmentSettingsUpdate>({
    mutationFn: (data) => recruitmentSettingsService.update(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: recruitmentSettingsKeys.all })
    },
  })
}
