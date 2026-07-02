"use client"

import * as React from "react"
import Link from "next/link"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { FEATURES } from "@/config/features"
import { AuthAlert } from "@/features/auth/auth-alert"
import { forgotPasswordSchema, type ForgotPasswordFormValues } from "@/features/auth/schemas"
import { authService } from "@/services/auth.service"
import type { ApiError } from "@/types"

function ForgotPasswordForm() {
  const [status, setStatus] = React.useState<
    { kind: "unavailable" | "sent" } | { kind: "error"; message: string } | null
  >(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  })

  async function onSubmit(values: ForgotPasswordFormValues) {
    if (!FEATURES.forgotPasswordEnabled) {
      setStatus({ kind: "unavailable" })
      return
    }
    try {
      await authService.forgotPassword(values.email)
      setStatus({ kind: "sent" })
    } catch (error) {
      const apiError = error as ApiError
      setStatus({ kind: "error", message: apiError?.message ?? "Something went wrong." })
    }
  }

  return (
    <form noValidate onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h1 className="text-h3 text-foreground">Forgot password</h1>
        <p className="text-sm text-muted-foreground">
          Enter your email and we&apos;ll send you instructions to reset your password.
        </p>
      </div>

      {status?.kind === "unavailable" && (
        <AuthAlert variant="info">
          Password reset isn&apos;t available yet. Please contact your organization
          administrator to reset your password.
        </AuthAlert>
      )}
      {status?.kind === "sent" && (
        <AuthAlert variant="info">
          If an account exists for that email, we&apos;ve sent reset instructions.
        </AuthAlert>
      )}
      {status?.kind === "error" && <AuthAlert variant="error">{status.message}</AuthAlert>}

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="forgot-email">Email</Label>
        <Input
          id="forgot-email"
          type="email"
          autoComplete="email"
          placeholder="you@company.com"
          aria-invalid={!!errors.email}
          aria-describedby={errors.email ? "forgot-email-error" : undefined}
          {...register("email")}
        />
        {errors.email && (
          <p id="forgot-email-error" className="text-xs text-destructive">
            {errors.email.message}
          </p>
        )}
      </div>

      <Button type="submit" isLoading={isSubmitting} className="w-full">
        Send reset instructions
      </Button>

      <Link href="/login" className="text-center text-sm text-primary hover:underline">
        Back to login
      </Link>
    </form>
  )
}

export { ForgotPasswordForm }
