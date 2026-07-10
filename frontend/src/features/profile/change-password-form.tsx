"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { PasswordInput } from "@/components/ui/password-input"
import { useChangePassword } from "@/hooks"

import { changePasswordFormSchema, type ChangePasswordFormValues } from "./schemas"

/** Shared by /profile and Settings > Security — don't duplicate. */
function ChangePasswordForm() {
  const changePassword = useChangePassword()
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordFormValues>({
    resolver: zodResolver(changePasswordFormSchema),
    defaultValues: { current_password: "", new_password: "", confirm_password: "" },
  })

  async function onSubmit(values: ChangePasswordFormValues) {
    try {
      await changePassword.mutateAsync({
        current_password: values.current_password,
        new_password: values.new_password,
      })
      toast.success("Password changed. Your other sessions have been signed out.")
      reset()
    } catch (error) {
      const message = error instanceof Error ? error.message : "Something went wrong"
      toast.error(message)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Change Password</CardTitle>
        <CardDescription>
          Changing your password signs you out of every other device.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form noValidate onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="current-password">Current Password</Label>
              <PasswordInput
                id="current-password"
                aria-invalid={!!errors.current_password}
                {...register("current_password")}
              />
              {errors.current_password && (
                <p className="text-xs text-destructive">{errors.current_password.message}</p>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="new-password">New Password</Label>
              <PasswordInput
                id="new-password"
                aria-invalid={!!errors.new_password}
                {...register("new_password")}
              />
              {errors.new_password && (
                <p className="text-xs text-destructive">{errors.new_password.message}</p>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="confirm-password">Confirm New Password</Label>
              <PasswordInput
                id="confirm-password"
                aria-invalid={!!errors.confirm_password}
                {...register("confirm_password")}
              />
              {errors.confirm_password && (
                <p className="text-xs text-destructive">{errors.confirm_password.message}</p>
              )}
            </div>
          </div>
          <div>
            <Button type="submit" isLoading={isSubmitting}>
              Change Password
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

export { ChangePasswordForm }
