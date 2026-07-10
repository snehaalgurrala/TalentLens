import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import {
  scoringRuleService,
  type ScoringRule,
  type ScoringRuleUpdatePayload,
  type ScoringRuleWeightsPayload,
} from "@/services/scoring-rule.service"
import type { ApiError } from "@/types"

export const scoringRuleKeys = {
  all: ["scoring-rule", "organization"] as const,
}

/** GET 404s when the org has never set a default — that's an expected empty
 * state (handled in the UI), not worth retrying. */
export function useScoringRule() {
  return useQuery<ScoringRule, ApiError>({
    queryKey: scoringRuleKeys.all,
    queryFn: scoringRuleService.getOrganizationDefault,
    retry: (failureCount, error) => error.status !== 404 && failureCount < 2,
  })
}

export function useCreateScoringRule() {
  const queryClient = useQueryClient()
  return useMutation<ScoringRule, ApiError, ScoringRuleWeightsPayload>({
    mutationFn: (data) => scoringRuleService.createOrganizationDefault(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: scoringRuleKeys.all })
    },
  })
}

export function useUpdateScoringRule() {
  const queryClient = useQueryClient()
  return useMutation<ScoringRule, ApiError, ScoringRuleUpdatePayload>({
    mutationFn: (data) => scoringRuleService.updateOrganizationDefault(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: scoringRuleKeys.all })
    },
  })
}
