import type { AssessmentSessionStatus } from "./assessment-session.types"

export type AssessmentInvitationStatus =
  | "PENDING"
  | "SENT"
  | "OPENED"
  | "STARTED"
  | "COMPLETED"
  | "EXPIRED"
  | "REVOKED"

export interface AssessmentInvitationSendRequest {
  campaign_id: string
  candidate_ids: string[]
  expiration_hours: number
}

export interface AssessmentInvitationSendSuccess {
  candidate_id: string
  invitation_id: string
}

export interface AssessmentInvitationSendFailure {
  candidate_id: string
  reason: string
}

export interface AssessmentInvitationSendResult {
  succeeded: AssessmentInvitationSendSuccess[]
  failed: AssessmentInvitationSendFailure[]
}

export interface AssessmentInvitationSessionInfo {
  id: string
  status: AssessmentSessionStatus
}

export interface AssessmentInvitationCampaignInfo {
  id: string
  title: string
}

export interface AssessmentInvitationDetail {
  assessment_session: AssessmentInvitationSessionInfo
  campaign: AssessmentInvitationCampaignInfo
  candidate_display_name: string
  status: AssessmentInvitationStatus
  expires_at: string
}
