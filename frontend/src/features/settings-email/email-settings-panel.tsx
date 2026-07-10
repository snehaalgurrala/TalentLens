"use client"

import * as React from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { Controller, useForm } from "react-hook-form"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { PasswordInput } from "@/components/ui/password-input"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { DashboardErrorState } from "@/features/dashboard"
import { usePlatformEmailConfig, useSendTestEmail, useUpdatePlatformEmailConfig } from "@/hooks"
import { formatDateTime } from "@/utils"
import type { PlatformEmailConfig, PlatformEmailConfigUpdate } from "@/types"

import { emailSettingsFormSchema, testEmailSchema, type EmailSettingsFormValues } from "./schemas"

function configToFormValues(config: PlatformEmailConfig): EmailSettingsFormValues {
  return {
    smtp_host: config.smtp_host,
    smtp_port: config.smtp_port.toString(),
    smtp_username: config.smtp_username,
    smtp_password: "",
    smtp_from_email: config.smtp_from_email,
    smtp_from_name: config.smtp_from_name,
    smtp_tls: config.smtp_tls,
    smtp_ssl: config.smtp_ssl,
  }
}

function toPayload(values: EmailSettingsFormValues): PlatformEmailConfigUpdate {
  const payload: PlatformEmailConfigUpdate = {
    smtp_host: values.smtp_host.trim(),
    smtp_port: Number(values.smtp_port),
    smtp_username: values.smtp_username || "",
    smtp_from_email: values.smtp_from_email.trim(),
    smtp_from_name: values.smtp_from_name || "",
    smtp_tls: values.smtp_tls,
    smtp_ssl: values.smtp_ssl,
  }
  if (values.smtp_password) {
    payload.smtp_password = values.smtp_password
  }
  return payload
}

function EmailSettingsPanelSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-4 w-72" />
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {Array.from({ length: 5 }).map((_, index) => (
            <Skeleton key={index} className="h-8 w-full" />
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

function TestEmailCard() {
  const [testEmail, setTestEmail] = React.useState("")
  const [validationError, setValidationError] = React.useState<string | null>(null)
  const sendTestEmail = useSendTestEmail()

  async function handleSendTest() {
    const result = testEmailSchema.safeParse(testEmail)
    if (!result.success) {
      setValidationError(result.error.issues[0]?.message ?? "Enter a valid email address")
      return
    }
    setValidationError(null)

    try {
      const response = await sendTestEmail.mutateAsync(result.data)
      if (response.success) {
        toast.success(`Test email sent to ${result.data}`)
      } else {
        toast.error(response.error ?? "Failed to send test email")
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Something went wrong"
      toast.error(message)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Test Email</CardTitle>
        <CardDescription>Send a test email using the SMTP settings currently saved.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-1.5">
        <Label htmlFor="test-email-recipient">Recipient</Label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            id="test-email-recipient"
            type="email"
            placeholder="you@example.com"
            className="sm:max-w-sm"
            value={testEmail}
            onChange={(event) => setTestEmail(event.target.value)}
            aria-invalid={!!validationError}
          />
          <Button
            type="button"
            variant="outline"
            isLoading={sendTestEmail.isPending}
            onClick={() => void handleSendTest()}
          >
            Send Test Email
          </Button>
        </div>
        {validationError && <p className="text-xs text-destructive">{validationError}</p>}
      </CardContent>
    </Card>
  )
}

function EmailSettingsPanel() {
  const { data, isLoading, isError, error, refetch } = usePlatformEmailConfig()
  const updateConfig = useUpdatePlatformEmailConfig()

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<EmailSettingsFormValues>({
    resolver: zodResolver(emailSettingsFormSchema),
    defaultValues: {
      smtp_host: "",
      smtp_port: "587",
      smtp_username: "",
      smtp_password: "",
      smtp_from_email: "",
      smtp_from_name: "",
      smtp_tls: true,
      smtp_ssl: false,
    },
  })

  React.useEffect(() => {
    if (data) reset(configToFormValues(data))
  }, [data, reset])

  async function onSubmit(values: EmailSettingsFormValues) {
    try {
      await updateConfig.mutateAsync(toPayload(values))
      toast.success("Email configuration updated")
    } catch (error) {
      const message = error instanceof Error ? error.message : "Something went wrong"
      toast.error(message)
    }
  }

  if (isLoading) return <EmailSettingsPanelSkeleton />
  if (isError) return <DashboardErrorState error={error} onRetry={() => void refetch()} />

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <form onSubmit={handleSubmit(onSubmit)}>
          <CardHeader>
            <div className="flex items-center justify-between gap-2">
              <CardTitle>Email Configuration</CardTitle>
              <Badge variant={data?.is_configured ? "active" : "outline"}>
                {data?.is_configured ? "Configured" : "Not Configured"}
              </Badge>
            </div>
            <CardDescription>
              SMTP settings used to send invitations and notifications. Visible to Super Admins only.
            </CardDescription>
          </CardHeader>

          <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email-smtp-host">SMTP Host</Label>
              <Input id="email-smtp-host" aria-invalid={!!errors.smtp_host} {...register("smtp_host")} />
              {errors.smtp_host && <p className="text-xs text-destructive">{errors.smtp_host.message}</p>}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email-smtp-port">SMTP Port</Label>
              <Input
                id="email-smtp-port"
                type="number"
                min={1}
                max={65535}
                aria-invalid={!!errors.smtp_port}
                {...register("smtp_port")}
              />
              {errors.smtp_port && <p className="text-xs text-destructive">{errors.smtp_port.message}</p>}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email-smtp-username">SMTP Username</Label>
              <Input id="email-smtp-username" {...register("smtp_username")} />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email-smtp-password">SMTP Password</Label>
              <PasswordInput
                id="email-smtp-password"
                placeholder={data?.has_password ? "••••••••" : "Not set"}
                {...register("smtp_password")}
              />
              <p className="text-xs text-muted-foreground">Leave blank to keep the existing password.</p>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email-smtp-from-email">From Email</Label>
              <Input
                id="email-smtp-from-email"
                type="email"
                aria-invalid={!!errors.smtp_from_email}
                {...register("smtp_from_email")}
              />
              {errors.smtp_from_email && (
                <p className="text-xs text-destructive">{errors.smtp_from_email.message}</p>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email-smtp-from-name">From Name</Label>
              <Input id="email-smtp-from-name" {...register("smtp_from_name")} />
            </div>

            <div className="flex items-center justify-between gap-4 rounded-lg border border-border p-3">
              <Label htmlFor="email-smtp-tls">Use TLS</Label>
              <Controller
                control={control}
                name="smtp_tls"
                render={({ field }) => (
                  <Switch id="email-smtp-tls" checked={field.value} onCheckedChange={field.onChange} />
                )}
              />
            </div>

            <div className="flex items-center justify-between gap-4 rounded-lg border border-border p-3">
              <Label htmlFor="email-smtp-ssl">Use SSL</Label>
              <Controller
                control={control}
                name="smtp_ssl"
                render={({ field }) => (
                  <Switch id="email-smtp-ssl" checked={field.value} onCheckedChange={field.onChange} />
                )}
              />
            </div>

            <div className="flex flex-col gap-1 rounded-lg border border-border p-3 text-xs text-muted-foreground sm:col-span-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-foreground">Last test:</span>
                <span>{data?.last_test_at ? formatDateTime(data.last_test_at) : "Never tested"}</span>
                {data?.last_test_status && (
                  <Badge variant={data.last_test_status === "success" ? "active" : "rejected"}>
                    {data.last_test_status === "success" ? "Success" : "Failed"}
                  </Badge>
                )}
              </div>
              {data?.last_test_error && <span className="text-destructive">{data.last_test_error}</span>}
            </div>
          </CardContent>

          <CardFooter>
            <Button type="submit" isLoading={isSubmitting}>
              Save Changes
            </Button>
          </CardFooter>
        </form>
      </Card>

      <TestEmailCard />
    </div>
  )
}

export { EmailSettingsPanel }
