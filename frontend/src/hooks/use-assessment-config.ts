import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { assessmentConfigService } from "@/services/settings.service"
import type { ApiError, AssessmentConfig, AssessmentConfigUpdate } from "@/types"

export const assessmentConfigKeys = {
  all: ["assessment-config"] as const,
}

export function useAssessmentConfig() {
  return useQuery<AssessmentConfig, ApiError>({
    queryKey: assessmentConfigKeys.all,
    queryFn: assessmentConfigService.get,
  })
}

export function useUpdateAssessmentConfig() {
  const queryClient = useQueryClient()
  return useMutation<AssessmentConfig, ApiError, AssessmentConfigUpdate>({
    mutationFn: (data) => assessmentConfigService.update(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: assessmentConfigKeys.all })
    },
  })
}
