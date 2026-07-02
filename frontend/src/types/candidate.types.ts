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
}

export interface UploadResponse {
  uploaded: ResumeFile[]
  count: number
}
