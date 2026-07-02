export type AssessmentStatus = "DRAFT" | "PUBLISHED" | "ARCHIVED"

export interface Assessment {
  id: string
  campaign_id: string
  title: string
  description: string | null
  status: AssessmentStatus
  created_at: string
  updated_at: string
}

export interface AssessmentCreate {
  campaign_id: string
  title: string
  description?: string | null
}

export interface AssessmentUpdate {
  title?: string
  description?: string | null
  status?: AssessmentStatus
}
