import type { PipelineStage } from "./candidate.types"
import type { UserSummary } from "./user.types"

export interface RecruiterWorkloadStageBreakdown {
  pipeline_stage: PipelineStage
  count: number
}

export interface RecruiterWorkloadItem {
  recruiter: UserSummary
  total_assigned: number
  by_stage: RecruiterWorkloadStageBreakdown[]
}

export interface RecruiterWorkloadResponse {
  items: RecruiterWorkloadItem[]
}
