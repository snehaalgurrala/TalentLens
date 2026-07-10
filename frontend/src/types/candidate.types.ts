import type { UserSummary } from "./user.types"

export interface RankingSubScores {
  semantic_score: number
  skills_score: number
  experience_score: number
  education_score: number
  projects_score: number
  certification_score: number
}

export type RankingRecommendation = "Strong Match" | "Good Match" | "Possible Match" | "Not a Match"

export type ScoringRuleSource = "campaign_override" | "organization_default" | "system_default"

export interface CandidateRanking {
  rank: number
  candidate_id: string
  candidate_name: string
  resume_file_id: string
  overall_score: number
  sub_scores: RankingSubScores
  recommendation: RankingRecommendation
  strengths: string[]
  weaknesses: string[]
  match_explanation: string
  scoring_rule_source: ScoringRuleSource
  current_company: string | null
  years_of_experience: number | null
  review_status: ReviewStatus
}

export type UploadStatus = "PENDING" | "UPLOADED" | "PROCESSING" | "PARSED" | "FAILED"

export type ReviewStatus = "PENDING" | "SHORTLISTED" | "REJECTED"

export type PipelineStage =
  | "APPLIED"
  | "PARSING"
  | "EMBEDDING"
  | "RANKED"
  | "SHORTLISTED"
  | "ASSESSMENT_SENT"
  | "ASSESSMENT_IN_PROGRESS"
  | "INTERVIEW_SCHEDULED"
  | "REJECTED"
  | "HIRED"
  | "ASSESSMENT_COMPLETED"
  | "INTERVIEW_COMPLETED"
  | "OFFER_EXTENDED"
  | "OFFER_ACCEPTED"
  | "WITHDRAWN"
  | "ARCHIVED"

export interface ResumeFile {
  id: string
  campaign_id: string
  original_filename: string
  stored_filename: string
  mime_type: string
  file_size: number
  storage_path: string
  upload_status: UploadStatus
  uploaded_by: string | null
  candidate_id: string | null
  error_message: string | null
  review_status: ReviewStatus
  is_deleted: boolean
  uploaded_at: string
  pipeline_stage: PipelineStage
  assigned_recruiter_id: string | null
  notes: string | null
}

export interface UploadResponse {
  uploaded: ResumeFile[]
  count: number
}

export interface EducationItem {
  institution: string | null
  degree: string | null
  field: string | null
}

export interface CandidateListItem {
  resume_file_id: string
  candidate_id: string
  candidate_name: string
  email: string | null
  phone: string | null
  location: string | null
  current_company: string | null
  current_role: string | null
  years_of_experience: number | null
  skills: string[]
  education: EducationItem[]

  rank: number | null
  overall_score: number | null
  sub_scores: RankingSubScores | null
  recommendation: RankingRecommendation | null

  upload_status: UploadStatus
  review_status: ReviewStatus
  pipeline_stage: PipelineStage
  assigned_recruiter: UserSummary | null
  notes: string | null
  applied_at: string
}

export interface CandidateListResponse {
  items: CandidateListItem[]
  total: number
  skip: number
  limit: number
  ranking_available: boolean
}

export interface CandidateListFilters {
  search?: string
  pipeline_stage?: PipelineStage
  review_status?: ReviewStatus
  assigned_recruiter_id?: string
  sort_by?: "overall_score" | "candidate_name" | "applied_at" | "years_of_experience"
  sort_dir?: "asc" | "desc"
  skip?: number
  limit?: number
}

export interface BulkActionFailure {
  id: string
  reason: string
}

export interface BulkActionResult {
  succeeded: string[]
  failed: BulkActionFailure[]
}
