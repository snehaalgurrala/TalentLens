import { z } from "zod"

// Mirrors backend/app/schemas/campaign.py::CampaignCreate constraints. Numeric
// fields stay as raw strings here (HTML number inputs + backend already
// enforce bounds) — converted to numbers in campaign-form.tsx::toPayload.
export const campaignFormSchema = z
  .object({
    title: z.string().min(1, "Campaign name is required").max(255),
    job_title: z.string().max(255).optional().or(z.literal("")),
    description: z.string().max(5000).optional().or(z.literal("")),
    department: z.string().max(120).optional().or(z.literal("")),
    hiring_manager_id: z.string().optional().or(z.literal("")),
    recruiter_id: z.string().optional().or(z.literal("")),
    employment_type: z
      .enum(["FULL_TIME", "PART_TIME", "CONTRACT", "INTERNSHIP", "TEMPORARY"])
      .optional()
      .or(z.literal("")),
    location: z.string().max(255).optional().or(z.literal("")),
    experience_min_years: z.string().optional().or(z.literal("")),
    experience_max_years: z.string().optional().or(z.literal("")),
    salary_min: z.string().optional().or(z.literal("")),
    salary_max: z.string().optional().or(z.literal("")),
    openings_count: z.string().min(1, "Required"),
    priority: z.enum(["LOW", "MEDIUM", "HIGH", "URGENT"]),
    closing_date: z.string().optional().or(z.literal("")),
    status: z.enum(["DRAFT", "ACTIVE", "PAUSED", "CLOSED", "ARCHIVED"]),
  })
  .refine(
    (data) =>
      !data.experience_min_years ||
      !data.experience_max_years ||
      Number(data.experience_max_years) >= Number(data.experience_min_years),
    { message: "Max experience must be greater than or equal to min experience", path: ["experience_max_years"] }
  )
  .refine(
    (data) => !data.salary_min || !data.salary_max || Number(data.salary_max) >= Number(data.salary_min),
    { message: "Max salary must be greater than or equal to min salary", path: ["salary_max"] }
  )

export type CampaignFormValues = z.infer<typeof campaignFormSchema>
