import { api } from "@/services/api"
import type {
  AssessmentInvitationDetail,
  AssessmentInvitationSendRequest,
  AssessmentInvitationSendResult,
} from "@/types"

export const assessmentInvitationService = {
  send: (data: AssessmentInvitationSendRequest) =>
    api.post<AssessmentInvitationSendResult>("/assessment/invitations/send", data),

  getByToken: (token: string) =>
    api.get<AssessmentInvitationDetail>(`/assessment/invitations/${token}`),

  markStarted: (token: string) =>
    api.post<AssessmentInvitationDetail>(`/assessment/invitations/${token}/start`),

  markCompleted: (token: string) =>
    api.post<AssessmentInvitationDetail>(`/assessment/invitations/${token}/complete`),
}
