"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { PasswordInput } from "@/components/ui/password-input"
import { AuthAlert } from "@/features/auth/auth-alert"
import {
  invitationRegisterSchema,
  type InvitationRegisterFormValues,
} from "@/features/auth/schemas"
import { authService } from "@/services/auth.service"
import type { ApiError } from "@/types"

interface InvitationRegisterFormProps {
  token: string
  email: string
  orgName: string
}

function registerErrorMessage(error: unknown): string {
  const apiError = error as ApiError
  switch (apiError?.status) {
    case 400:
      return "This invitation is invalid, expired, or has already been used."
    case 409:
      return "An account with this email already exists."
    case 422:
      return apiError.message || "Please check your details and try again."
    case 0:
      return "Unable to reach the server. Check your connection and try again."
    default:
      return apiError?.message ?? "Something went wrong. Please try again."
  }
}

/**
 * Ends by redirecting to /login rather than auto-authenticating — calls
 * `authService.register` directly instead of `useAuth().register` (which
 * signs the user in), per the invitation flow's "redirect to login" UX.
 */
function InvitationRegisterForm({ token, email, orgName }: InvitationRegisterFormProps) {
  const router = useRouter()
  const [formError, setFormError] = React.useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<InvitationRegisterFormValues>({
    resolver: zodResolver(invitationRegisterSchema),
    defaultValues: { fullName: "", password: "", confirmPassword: "" },
  })

  async function onSubmit(values: InvitationRegisterFormValues) {
    setFormError(null)
    try {
      await authService.register({
        email,
        password: values.password,
        full_name: values.fullName,
        invitation_token: token,
      })
      toast.success("Account created. Please log in.")
      router.replace("/login")
    } catch (error) {
      setFormError(registerErrorMessage(error))
    }
  }

  return (
    <form noValidate onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h1 className="text-h3 text-foreground">Join {orgName}</h1>
        <p className="text-sm text-muted-foreground">
          You&apos;ve been invited as <span className="font-medium text-foreground">{email}</span>.
          Create a password to finish setting up your account.
        </p>
      </div>

      {formError && <AuthAlert variant="error">{formError}</AuthAlert>}

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="invite-full-name">Full name</Label>
        <Input
          id="invite-full-name"
          autoComplete="name"
          placeholder="Jane Doe"
          aria-invalid={!!errors.fullName}
          aria-describedby={errors.fullName ? "invite-full-name-error" : undefined}
          {...register("fullName")}
        />
        {errors.fullName && (
          <p id="invite-full-name-error" className="text-xs text-destructive">
            {errors.fullName.message}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="invite-password">Password</Label>
        <PasswordInput
          id="invite-password"
          autoComplete="new-password"
          placeholder="••••••••"
          aria-invalid={!!errors.password}
          aria-describedby={errors.password ? "invite-password-error" : undefined}
          {...register("password")}
        />
        {errors.password && (
          <p id="invite-password-error" className="text-xs text-destructive">
            {errors.password.message}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="invite-confirm-password">Confirm password</Label>
        <PasswordInput
          id="invite-confirm-password"
          autoComplete="new-password"
          placeholder="••••••••"
          aria-invalid={!!errors.confirmPassword}
          aria-describedby={errors.confirmPassword ? "invite-confirm-password-error" : undefined}
          {...register("confirmPassword")}
        />
        {errors.confirmPassword && (
          <p id="invite-confirm-password-error" className="text-xs text-destructive">
            {errors.confirmPassword.message}
          </p>
        )}
      </div>

      <Button type="submit" isLoading={isSubmitting} className="w-full">
        Create account
      </Button>
    </form>
  )
}

export { InvitationRegisterForm }
