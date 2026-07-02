"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { zodResolver } from "@hookform/resolvers/zod"
import { Controller, useForm } from "react-hook-form"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { PasswordInput } from "@/components/ui/password-input"
import { AuthAlert } from "@/features/auth/auth-alert"
import { loginSchema, type LoginFormValues } from "@/features/auth/schemas"
import { useAuth } from "@/hooks/use-auth"
import { DEFAULT_AUTHENTICATED_ROUTE } from "@/lib/constants"
import type { ApiError } from "@/types"

/** Only allow same-origin, absolute-path redirects — never hand a bare `redirect` param to the router. */
function sanitizeRedirect(target: string | null): string {
  if (!target || !target.startsWith("/") || target.startsWith("//")) {
    return DEFAULT_AUTHENTICATED_ROUTE
  }
  return target
}

function loginErrorMessage(error: unknown): string {
  const apiError = error as ApiError
  switch (apiError?.status) {
    case 401:
      return "Invalid email or password."
    case 403:
      return "This account has been deactivated. Contact your administrator."
    case 0:
      return "Unable to reach the server. Check your connection and try again."
    default:
      return apiError?.message ?? "Something went wrong. Please try again."
  }
}

function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { login } = useAuth()
  const [formError, setFormError] = React.useState<string | null>(null)

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "", rememberMe: true },
  })

  async function onSubmit(values: LoginFormValues) {
    setFormError(null)
    try {
      await login({ email: values.email, password: values.password }, values.rememberMe)
      toast.success("Welcome back")
      router.replace(sanitizeRedirect(searchParams.get("redirect")))
    } catch (error) {
      setFormError(loginErrorMessage(error))
    }
  }

  return (
    <form noValidate onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h1 className="text-h3 text-foreground">Welcome back</h1>
        <p className="text-sm text-muted-foreground">Log in to your TalentSmart account.</p>
      </div>

      {formError && <AuthAlert variant="error">{formError}</AuthAlert>}

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="login-email">Email</Label>
        <Input
          id="login-email"
          type="email"
          autoComplete="email"
          placeholder="you@company.com"
          aria-invalid={!!errors.email}
          aria-describedby={errors.email ? "login-email-error" : undefined}
          {...register("email")}
        />
        {errors.email && (
          <p id="login-email-error" className="text-xs text-destructive">
            {errors.email.message}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="login-password">Password</Label>
        <PasswordInput
          id="login-password"
          autoComplete="current-password"
          placeholder="••••••••"
          aria-invalid={!!errors.password}
          aria-describedby={errors.password ? "login-password-error" : undefined}
          {...register("password")}
        />
        {errors.password && (
          <p id="login-password-error" className="text-xs text-destructive">
            {errors.password.message}
          </p>
        )}
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Controller
            control={control}
            name="rememberMe"
            render={({ field }) => (
              <Checkbox
                id="login-remember"
                checked={field.value}
                onCheckedChange={(checked) => field.onChange(checked === true)}
              />
            )}
          />
          <Label htmlFor="login-remember" className="font-normal text-muted-foreground">
            Remember me
          </Label>
        </div>
        <Link href="/forgot-password" className="text-sm text-primary hover:underline">
          Forgot password?
        </Link>
      </div>

      <Button type="submit" isLoading={isSubmitting} className="w-full">
        Log in
      </Button>
    </form>
  )
}

export { LoginForm }
