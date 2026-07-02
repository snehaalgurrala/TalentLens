import type { UserSummary } from "@/types/user.types"

export type CampaignStatus = "DRAFT" | "ACTIVE" | "PAUSED" | "CLOSED" | "ARCHIVED"

export type EmploymentType = "FULL_TIME" | "PART_TIME" | "CONTRACT" | "INTERNSHIP" | "TEMPORARY"

export type CampaignPriority = "LOW" | "MEDIUM" | "HIGH" | "URGENT"

export interface Campaign {
  id: string
  org_id: string
  created_by: string | null
  title: string
  description: string | null
  status: CampaignStatus
  is_deleted: boolean
  created_at: string
  updated_at: string

  job_title: string | null
  department: string | null
  hiring_manager_id: string | null
  recruiter_id: string | null
  employment_type: EmploymentType | null
  location: string | null
  experience_min_years: number | null
  experience_max_years: number | null
  salary_min: number | null
  salary_max: number | null
  openings_count: number
  priority: CampaignPriority
  closing_date: string | null

  hiring_manager: UserSummary | null
  recruiter: UserSummary | null
  resume_count: number
  processing_resume_count: number
}

export interface CampaignCreate {
  title: string
  description?: string | null
  status?: CampaignStatus
  job_title?: string | null
  department?: string | null
  hiring_manager_id?: string | null
  recruiter_id?: string | null
  employment_type?: EmploymentType | null
  location?: string | null
  experience_min_years?: number | null
  experience_max_years?: number | null
  salary_min?: number | null
  salary_max?: number | null
  openings_count?: number
  priority?: CampaignPriority
  closing_date?: string | null
}

export type CampaignUpdate = Partial<CampaignCreate>

export interface CampaignFilters {
  skip?: number
  limit?: number
  search?: string
  status?: CampaignStatus
  department?: string
  employment_type?: EmploymentType
  priority?: CampaignPriority
  recruiter_id?: string
  hiring_manager_id?: string
  created_after?: string
  created_before?: string
  sort_by?: "created_at" | "updated_at" | "title" | "status" | "priority"
  sort_dir?: "asc" | "desc"
}

export interface CampaignSummary {
  total_candidates: number
  processing_candidates: number
  ranked_candidates: number
  shortlisted_candidates: number
  rejected_candidates: number
  average_match_score: number | null
}

export interface CampaignProcessingStatus {
  uploaded_count: number
  parsing_count: number
  embedding_count: number
  ready_for_ranking_count: number
  completed_count: number
  failed_count: number
  total_count: number
}
