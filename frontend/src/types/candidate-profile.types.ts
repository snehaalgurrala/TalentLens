import type { RankingRecommendation, RankingSubScores, ReviewStatus, PipelineStage, UploadStatus } from "./candidate.types"
import type { UserSummary } from "./user.types"

// ── Structured resume content (mirrors the backend's StructuredResume exactly) ─

export interface StructuredExperienceItem {
  company: string | null
  role: string | null
  start_date: string | null
  end_date: string | null
  description: string | null
}

export interface StructuredEducationEntry {
  institution: string | null
  degree: string | null
  field: string | null
  graduation_year: string | null
}

export interface StructuredProjectItem {
  name: string | null
  description: string | null
  technologies: string[]
}

export interface StructuredCertificationItem {
  name: string | null
  issuer: string | null
  date: string | null
}

export interface StructuredResumeContent {
  skills: string[]
  experience: StructuredExperienceItem[]
  education: StructuredEducationEntry[]
  projects: StructuredProjectItem[]
  certifications: StructuredCertificationItem[]
  summary: string | null
}

export interface CandidateProfileCampaign {
  id: string
  title: string
}

// ── Full profile ──────────────────────────────────────────────────────────────

export interface CandidateProfile {
  resume_file_id: string
  candidate_id: string
  candidate_name: string
  email: string | null
  phone: string | null
  location: string | null
  linkedin_url: string | null
  github_url: string | null
  current_company: string | null
  current_role: string | null
  years_of_experience: number | null

  structured_resume: StructuredResumeContent
  parse_confidence: number | null

  campaign: CandidateProfileCampaign
  upload_status: UploadStatus
  review_status: ReviewStatus
  pipeline_stage: PipelineStage
  assigned_recruiter: UserSummary | null
  uploaded_at: string

  overall_score: number | null
  sub_scores: RankingSubScores | null
  recommendation: RankingRecommendation | null
  ranking_available: boolean
}

// ── AI match analysis (single candidate) ─────────────────────────────────────

export type MatchSentiment = "positive" | "negative" | "neutral"

export interface MatchExplanationItem {
  text: string
  sentiment: MatchSentiment
  category: string
}

export interface CandidateMatchAnalysis {
  overall_score: number
  recommendation: RankingRecommendation
  sub_scores: RankingSubScores
  bonus_points: number
  preferred_company_matched: boolean
  scoring_rule_source: "campaign_override" | "organization_default" | "system_default"
  match_explanation: string
  strengths: string[]
  weaknesses: string[]

  semantic_details: {
    cosine_similarity?: number
    cosine_score?: number
    domain_relevance_score?: number
    cosine_weight?: number
    domain_weight?: number
    industry?: string | null
  }
  skills_details: {
    required?: SkillCoverageDetail
    preferred?: SkillCoverageDetail
  }
  experience_details: {
    candidate_years?: number
    required_min_years?: number
    required_max_years?: number
  }
  education_details: { requirements?: RequirementCredit[] }
  projects_details: { requirements?: RequirementCredit[] }
  certification_details: { required?: string[]; matched?: string[]; missing?: string[] }

  explanation_items: MatchExplanationItem[]
}

export interface SkillCoverageDetail {
  skills: string[]
  exact_matches: string[]
  synonym_matches: { skill: string; matched_to: string }[]
  partial_matches: { skill: string; matched_to: string }[]
  missing: string[]
}

export interface RequirementCredit {
  requirement: string
  credit: number
  best_match: Record<string, unknown> | null
}

// ── Notes ─────────────────────────────────────────────────────────────────────

export interface CandidateNote {
  id: string
  resume_file_id: string
  author: UserSummary | null
  body: string
  created_at: string
  updated_at: string
  can_edit: boolean
  is_pinned: boolean
  mentioned_user_ids: string[]
}

// ── Activity ──────────────────────────────────────────────────────────────────

export type ActivityEventType =
  | "RESUME_UPLOADED"
  | "PARSING_STARTED"
  | "PARSED"
  | "PARSE_FAILED"
  | "RANKED"
  | "VIEWED"
  | "SHORTLISTED"
  | "REJECTED"
  | "PIPELINE_STAGE_CHANGED"
  | "RECRUITER_ASSIGNED"
  | "NOTE_ADDED"
  | "ARCHIVED"
  | "RESTORED"
  | "TASK_CREATED"
  | "TASK_COMPLETED"
  | "TASK_REASSIGNED"

export interface CandidateActivity {
  id: string
  event_type: ActivityEventType
  actor: UserSummary | null
  event_metadata: Record<string, unknown> | null
  created_at: string
}

// ── Tasks ─────────────────────────────────────────────────────────────────────

export type TaskPriority = "LOW" | "MEDIUM" | "HIGH" | "URGENT"

export type TaskStatus = "OPEN" | "IN_PROGRESS" | "COMPLETED"

export interface CandidateTask {
  id: string
  resume_file_id: string
  title: string
  description: string | null
  due_date: string | null
  priority: TaskPriority
  status: TaskStatus
  assignee: UserSummary | null
  created_by: UserSummary | null
  completed_at: string | null
  created_at: string
  updated_at: string
}
