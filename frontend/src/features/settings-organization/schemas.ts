import { z } from "zod"

// Mirrors backend/app/schemas/organization.py::OrganizationUpdate — all fields
// are plain optional strings, backend enforces any deeper validation.
export const organizationFormSchema = z.object({
  name: z.string().min(1, "Organization name is required").max(255),
  industry: z.string().max(120).optional().or(z.literal("")),
  website: z.string().max(255).optional().or(z.literal("")),
  company_email: z
    .string()
    .max(255)
    .optional()
    .or(z.literal(""))
    .refine((value) => !value || z.string().email().safeParse(value).success, {
      message: "Enter a valid email address",
    }),
  phone: z.string().max(50).optional().or(z.literal("")),
  address_line1: z.string().max(255).optional().or(z.literal("")),
  address_line2: z.string().max(255).optional().or(z.literal("")),
  city: z.string().max(120).optional().or(z.literal("")),
  state: z.string().max(120).optional().or(z.literal("")),
  postal_code: z.string().max(30).optional().or(z.literal("")),
  country: z.string().max(120).optional().or(z.literal("")),
  timezone: z.string().max(120).optional().or(z.literal("")),
  description: z.string().max(5000).optional().or(z.literal("")),
})

export type OrganizationFormValues = z.infer<typeof organizationFormSchema>
