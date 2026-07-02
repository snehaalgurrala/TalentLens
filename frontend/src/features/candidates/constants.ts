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
