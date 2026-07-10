import { z } from "zod"

// Mirrors backend/app/schemas/scoring_rule.py — weights are 0..1 floats that
// must sum to exactly 1.0 (within WEIGHT_SUM_TOLERANCE); enforced client-side
// too so the live sum indicator and the submit button agree with the API.
export const scoringWeightsFormSchema = z.object({
  semantic_weight: z.string().min(1, "Required"),
  skills_weight: z.string().min(1, "Required"),
  experience_weight: z.string().min(1, "Required"),
  education_weight: z.string().min(1, "Required"),
  project_weight: z.string().min(1, "Required"),
  certification_weight: z.string().min(1, "Required"),
  preferred_company_bonus: z.string().min(1, "Required"),
})

export type ScoringWeightsFormValues = z.infer<typeof scoringWeightsFormSchema>

export const WEIGHT_FIELD_KEYS = [
  "semantic_weight",
  "skills_weight",
  "experience_weight",
  "education_weight",
  "project_weight",
  "certification_weight",
] as const

export const WEIGHT_SUM_TOLERANCE = 0.001
export const MAX_PREFERRED_COMPANY_BONUS = 0.05

// Mirrors backend/app/schemas/settings.py::RecruitmentSettingsUpdate.
export const recruitmentPolicyFormSchema = z.object({
  default_resume_score_threshold: z.string().min(1, "Required"),
  enable_explainable_ai: z.boolean(),
  max_resume_upload_count: z.string().min(1, "Required"),
  max_resume_size_mb: z.string().min(1, "Required"),
  supported_resume_formats: z.array(z.string()).min(1, "Select at least one format"),
})

export type RecruitmentPolicyFormValues = z.infer<typeof recruitmentPolicyFormSchema>
