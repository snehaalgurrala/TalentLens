"use client"

import { toast } from "sonner"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { DashboardErrorState } from "@/features/dashboard"
import { useNotificationPreferences, useUpdateNotificationPreferences } from "@/hooks"
import { cn } from "@/lib/utils"
import type { NotificationPreference, NotificationPreferenceUpdate } from "@/types"

type EventKey =
  | "assessment_completed"
  | "assessment_started"
  | "invitation_sent"
  | "invitation_opened"
  | "candidate_shortlisted"
  | "ai_ranking_completed"
  | "daily_summary"
  | "weekly_summary"

const EVENT_OPTIONS: { key: EventKey; label: string; description: string }[] = [
  {
    key: "assessment_completed",
    label: "Assessment Completed",
    description: "A candidate finishes an assessment.",
  },
  {
    key: "assessment_started",
    label: "Assessment Started",
    description: "A candidate starts an assessment.",
  },
  { key: "invitation_sent", label: "Invitation Sent", description: "An assessment invitation is sent." },
  {
    key: "invitation_opened",
    label: "Invitation Opened",
    description: "A candidate opens their invitation.",
  },
  {
    key: "candidate_shortlisted",
    label: "Candidate Shortlisted",
    description: "A candidate is shortlisted.",
  },
  {
    key: "ai_ranking_completed",
    label: "AI Ranking Completed",
    description: "AI ranking finishes for a campaign.",
  },
  { key: "daily_summary", label: "Daily Summary", description: "A daily digest of recruiting activity." },
  {
    key: "weekly_summary",
    label: "Weekly Summary",
    description: "A weekly digest of recruiting activity.",
  },
]

function NotificationSettingsPanelSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-4 w-72" />
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-8 w-full" />
        ))}
      </CardContent>
    </Card>
  )
}

function NotificationSettingsPanel() {
  const { data, isLoading, isError, error, refetch } = useNotificationPreferences()
  const updatePreferences = useUpdateNotificationPreferences()

  function handleToggle(key: keyof NotificationPreference, checked: boolean) {
    const update: NotificationPreferenceUpdate = { [key]: checked }
    updatePreferences.mutate(update, {
      onError: (err) => toast.error(err.message || "Failed to update notification preference"),
    })
  }

  if (isLoading) return <NotificationSettingsPanelSkeleton />
  if (isError) return <DashboardErrorState error={error} onRetry={() => void refetch()} />
  if (!data) return null

  const mastersOff = !data.email_enabled && !data.in_app_enabled

  return (
    <Card>
      <CardHeader>
        <CardTitle>Notification Settings</CardTitle>
        <CardDescription>Choose how and when you&rsquo;re notified about recruiting activity.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-3 rounded-lg border border-border p-3">
          <div className="flex items-center justify-between gap-4">
            <div className="flex flex-col gap-0.5">
              <Label htmlFor="notif-email-enabled">Email Notifications</Label>
              <p className="text-xs text-muted-foreground">Receive notifications by email.</p>
            </div>
            <Switch
              id="notif-email-enabled"
              checked={data.email_enabled}
              disabled={updatePreferences.isPending}
              onCheckedChange={(checked) => handleToggle("email_enabled", checked)}
            />
          </div>
          <div className="flex items-center justify-between gap-4">
            <div className="flex flex-col gap-0.5">
              <Label htmlFor="notif-in-app-enabled">In-App Notifications</Label>
              <p className="text-xs text-muted-foreground">Receive notifications inside TalentLens.</p>
            </div>
            <Switch
              id="notif-in-app-enabled"
              checked={data.in_app_enabled}
              disabled={updatePreferences.isPending}
              onCheckedChange={(checked) => handleToggle("in_app_enabled", checked)}
            />
          </div>
        </div>

        <div
          className={cn("grid grid-cols-1 gap-3 transition-opacity sm:grid-cols-2", mastersOff && "opacity-50")}
        >
          {EVENT_OPTIONS.map((option) => (
            <div
              key={option.key}
              className="flex items-center justify-between gap-4 rounded-lg border border-border p-3"
            >
              <div className="flex flex-col gap-0.5">
                <Label htmlFor={`notif-${option.key}`}>{option.label}</Label>
                <p className="text-xs text-muted-foreground">{option.description}</p>
              </div>
              <Switch
                id={`notif-${option.key}`}
                checked={data[option.key]}
                disabled={updatePreferences.isPending}
                onCheckedChange={(checked) => handleToggle(option.key, checked)}
              />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

export { NotificationSettingsPanel }
