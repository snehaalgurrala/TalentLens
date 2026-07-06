import type { ComponentProps } from "react"

import type { Badge } from "@/components/ui/badge"
import type { PipelineStage, RankingRecommendation, ReviewStatus } from "@/types"

type BadgeVariant = ComponentProps<typeof Badge>["variant"]

export const PIPELINE_STAGE_LABELS: Record<PipelineStage, string> = {
  APPLIED: "Applied",
  PARSING: "Parsing",
  EMBEDDING: "Embedding",
  RANKED: "Ranked",
  SHORTLISTED: "Shortlisted",
  ASSESSMENT_SENT: "Assessment Sent",
  INTERVIEW_SCHEDULED: "Interview Scheduled",
  REJECTED: "Rejected",
  HIRED: "Hired",
  ASSESSMENT_COMPLETED: "Assessment Completed",
  INTERVIEW_COMPLETED: "Interview Completed",
  OFFER_EXTENDED: "Offer Extended",
  OFFER_ACCEPTED: "Offer Accepted",
  WITHDRAWN: "Withdrawn",
  ARCHIVED: "Archived",
}

export const PIPELINE_STAGE_OPTIONS: { value: PipelineStage; label: string }[] = (
  Object.entries(PIPELINE_STAGE_LABELS) as [PipelineStage, string][]
).map(([value, label]) => ({ value, label }))

export const PIPELINE_STAGE_VARIANT: Record<PipelineStage, BadgeVariant> = {
  APPLIED: "secondary",
  PARSING: "pending",
  EMBEDDING: "pending",
  RANKED: "outline",
  SHORTLISTED: "shortlisted",
  ASSESSMENT_SENT: "warning",
  INTERVIEW_SCHEDULED: "active",
  REJECTED: "rejected",
  HIRED: "success",
  ASSESSMENT_COMPLETED: "warning",
  INTERVIEW_COMPLETED: "active",
  OFFER_EXTENDED: "success",
  OFFER_ACCEPTED: "success",
  WITHDRAWN: "secondary",
  ARCHIVED: "secondary",
}

export const RECOMMENDATION_VARIANT: Record<RankingRecommendation, BadgeVariant> = {
  "Strong Match": "active",
  "Good Match": "success",
  "Possible Match": "pending",
  "Not a Match": "destructive",
}

export const REVIEW_STATUS_VARIANT: Record<ReviewStatus, BadgeVariant> = {
  PENDING: "secondary",
  SHORTLISTED: "shortlisted",
  REJECTED: "rejected",
}

export const REVIEW_STATUS_OPTIONS: { value: ReviewStatus; label: string }[] = [
  { value: "PENDING", label: "Pending" },
  { value: "SHORTLISTED", label: "Shortlisted" },
  { value: "REJECTED", label: "Rejected" },
]

/** Terminal pipeline stages — a candidate here has left the active pipeline
 * and can only move forward again via Restore. */
export const TERMINAL_STAGES: ReadonlySet<PipelineStage> = new Set([
  "REJECTED",
  "WITHDRAWN",
  "ARCHIVED",
])
