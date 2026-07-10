import { api } from "@/services/api"
import type { AssessmentAnalytics } from "@/types"

export const assessmentAnalyticsService = {
  getSummary: (campaignId?: string) =>
    api.get<AssessmentAnalytics>("/assessment/analytics", {
      params: campaignId ? { campaign_id: campaignId } : undefined,
    }),
}
