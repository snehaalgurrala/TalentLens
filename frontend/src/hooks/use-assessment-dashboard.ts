import { useQuery } from "@tanstack/react-query"

import { assessmentDashboardService } from "@/services/assessment-dashboard.service"
import type { ApiError, AssessmentSession, AssessmentSessionFull } from "@/types"

export const assessmentDashboardKeys = {
  all: ["assessment-dashboard"] as const,
  full: (sessionId: string) => [...assessmentDashboardKeys.all, "full", sessionId] as const,
  byCandidate: (candidateId: string, campaignId: string) =>
    [...assessmentDashboardKeys.all, "by-candidate", candidateId, campaignId] as const,
}

export function useAssessmentSessionFull(sessionId: string | undefined) {
  return useQuery<AssessmentSessionFull, ApiError>({
    queryKey: assessmentDashboardKeys.full(sessionId ?? ""),
    queryFn: () => assessmentDashboardService.getFull(sessionId as string),
    enabled: Boolean(sessionId),
  })
}

/** A 404 here means "assessment not started for this candidate" — an
 * expected state, not a transient error, so retries are disabled (same
 * treatment as useCandidateMatchAnalysis's 422 handling). */
export function useAssessmentSessionByCandidate(
  candidateId: string | undefined,
  campaignId: string | undefined
) {
  return useQuery<AssessmentSession, ApiError>({
    queryKey: assessmentDashboardKeys.byCandidate(candidateId ?? "", campaignId ?? ""),
    queryFn: () => assessmentDashboardService.getSessionByCandidate(candidateId as string, campaignId as string),
    enabled: Boolean(candidateId && campaignId),
    retry: false,
  })
}
