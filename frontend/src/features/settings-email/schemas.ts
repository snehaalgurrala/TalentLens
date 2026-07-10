import { z } from "zod"

// smtp_port stays a raw string here (HTML number input) — converted to a
// number in email-settings-panel.tsx::toPayload. smtp_password is optional:
// the API never returns it, so an empty value means "keep the existing one".
export const emailSettingsFormSchema = z.object({
  smtp_host: z.string().min(1, "SMTP host is required").max(255),
  smtp_port: z
    .string()
    .min(1, "Required")
    .refine(
      (v) => !Number.isNaN(Number(v)) && Number.isInteger(Number(v)) && Number(v) > 0 && Number(v) <= 65535,
      { message: "Port must be a whole number between 1 and 65535" }
    ),
  smtp_username: z.string().max(255).optional().or(z.literal("")),
  smtp_password: z.string().max(255).optional().or(z.literal("")),
  smtp_from_email: z.string().min(1, "From email is required").email("Enter a valid email address"),
  smtp_from_name: z.string().max(255).optional().or(z.literal("")),
  smtp_tls: z.boolean(),
  smtp_ssl: z.boolean(),
})

export type EmailSettingsFormValues = z.infer<typeof emailSettingsFormSchema>

export const testEmailSchema = z.string().min(1, "Enter an email address").email("Enter a valid email address")
