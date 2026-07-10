import { z } from "zod"

export const profileFormSchema = z.object({
  full_name: z.string().min(1, "Full name is required").max(255),
})

export type ProfileFormValues = z.infer<typeof profileFormSchema>

export const changePasswordFormSchema = z
  .object({
    current_password: z.string().min(1, "Current password is required"),
    new_password: z.string().min(8, "New password must be at least 8 characters").max(128),
    confirm_password: z.string().min(1, "Please confirm your new password"),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  })

export type ChangePasswordFormValues = z.infer<typeof changePasswordFormSchema>
