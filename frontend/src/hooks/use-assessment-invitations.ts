import { useMutation, useQuery } from "@tanstack/react-query"

import { assessmentInvitationService } from "@/services/assessment-invitation.service"
import { useInvalidateAfterMutation } from "@/hooks/use-candidate-management"
import type {
  ApiError,
  AssessmentInvitationDetail,
  AssessmentInvitationSendRequest,
  AssessmentInvitationSendResult,
} from "@/types"

export const assessmentInvitationKeys = {
  all: ["assessment-invitation"] as const,
  byToken: (token: string) => [...assessmentInvitationKeys.all, "by-token", token] as const,
}

/** A successful send moves candidates to ASSESSMENT_SENT server-side (see
 * AssessmentInvitationService._send_one) — invalidate the same query keys
 * every other pipeline-stage-mutating hook does, so the Pipeline Board and
 * candidate list pick up the new stage without a manual refresh. */
export function useSendAssessmentInvitations() {
  const invalidate = useInvalidateAfterMutation()
  return useMutation<AssessmentInvitationSendResult, ApiError, AssessmentInvitationSendRequest>({
    mutationFn: (data) => assessmentInvitationService.send(data),
    onSuccess: invalidate,
  })
}

/** A 404/410 here is an expected candidate-facing state (invalid, expired,
 * revoked, or already-completed link), not a transient error, so retries are
 * disabled — same treatment as useAssessmentSessionByCandidate's 404. */
export function useInvitationByToken(token: string) {
  return useQuery<AssessmentInvitationDetail, ApiError>({
    queryKey: assessmentInvitationKeys.byToken(token),
    queryFn: () => assessmentInvitationService.getByToken(token),
    enabled: Boolean(token),
    retry: false,
  })
}

export function useMarkInvitationStarted() {
  return useMutation<AssessmentInvitationDetail, ApiError, string>({
    mutationFn: (token) => assessmentInvitationService.markStarted(token),
  })
}

export function useMarkInvitationCompleted() {
  return useMutation<AssessmentInvitationDetail, ApiError, string>({
    mutationFn: (token) => assessmentInvitationService.markCompleted(token),
  })
}
