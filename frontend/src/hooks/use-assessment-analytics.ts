import { useQuery } from "@tanstack/react-query"

import { assessmentAnalyticsService } from "@/services/assessment-analytics.service"
import type { ApiError, AssessmentAnalytics } from "@/types"

export const assessmentAnalyticsKeys = {
  all: ["assessment-analytics"] as const,
  summary: (campaignId?: string) =>
    [...assessmentAnalyticsKeys.all, "summary", campaignId ?? "all"] as const,
}

export function useAssessmentAnalytics(campaignId?: string) {
  return useQuery<AssessmentAnalytics, ApiError>({
    queryKey: assessmentAnalyticsKeys.summary(campaignId),
    queryFn: () => assessmentAnalyticsService.getSummary(campaignId),
  })
}
