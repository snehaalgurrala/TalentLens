import type { CampaignStatus } from "@/types/campaign.types"

export interface DashboardSummary {
  total_campaigns: number
  active_campaigns: number
  closed_campaigns: number
  total_candidates: number
  processing_candidates: number
  shortlisted_candidates: number
  rejected_candidates: number
  average_match_score: number | null
}

export interface RecentCampaign {
  id: string
  title: string
  status: CampaignStatus
  created_at: string
  candidate_count: number
}

export type CandidateReviewStatus = "PENDING" | "SHORTLISTED" | "REJECTED"

export interface TopCandidate {
  candidate_id: string
  candidate_name: string
  resume_file_id: string
  match_score: number
  campaign_id: string
  campaign_name: string
  years_of_experience: number | null
  current_company: string | null
  review_status: CandidateReviewStatus
}

export interface ProcessingStatus {
  parsing_queue: number
  embedding_queue: number
  ranking_queue: number
  failed_jobs: number
  completed_jobs: number
}

export type DashboardActivityType =
  | "CAMPAIGN_CREATED"
  | "RESUME_UPLOADED"
  | "CANDIDATE_SHORTLISTED"
  | "CANDIDATE_REJECTED"

export interface DashboardActivityItem {
  id: string
  type: DashboardActivityType
  description: string
  occurred_at: string
  campaign_id: string | null
  campaign_name: string | null
}
