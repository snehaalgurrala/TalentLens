import { api } from "@/services/api"

export interface ScoringRule {
  id: string
  org_id: string
  campaign_id: string | null
  created_by: string | null
  semantic_weight: number
  skills_weight: number
  experience_weight: number
  education_weight: number
  project_weight: number
  certification_weight: number
  preferred_company_bonus: number
  preferred_companies: string[]
  created_at: string
  updated_at: string
}

export interface ScoringRuleWeightsPayload {
  semantic_weight: number
  skills_weight: number
  experience_weight: number
  education_weight: number
  project_weight: number
  certification_weight: number
  preferred_company_bonus: number
  preferred_companies: string[]
}

export type ScoringRuleUpdatePayload = Partial<ScoringRuleWeightsPayload>

export const scoringRuleService = {
  getOrganizationDefault: () => api.get<ScoringRule>("/scoring-rules/organization"),
  createOrganizationDefault: (data: ScoringRuleWeightsPayload) =>
    api.post<ScoringRule>("/scoring-rules/organization", data),
  updateOrganizationDefault: (data: ScoringRuleUpdatePayload) =>
    api.patch<ScoringRule>("/scoring-rules/organization", data),
}
