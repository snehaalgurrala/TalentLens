"use client"

import { Trophy } from "lucide-react"

import { Skeleton } from "@/components/ui/skeleton"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { Stack } from "@/components/layout/stack"
import { DashboardErrorState } from "@/features/dashboard"
import { useCandidateActivity } from "@/hooks"
import { cn } from "@/lib/utils"
import { ACTIVITY_ICON, ACTIVITY_ICON_STYLE, ACTIVITY_LABELS } from "@/features/candidate-profile/constants"

export interface ActivityTabProps {
  candidateId: string
}

function formatRelativeTime(iso: string): string {
  const date = new Date(iso)
  const diffMinutes = Math.round((Date.now() - date.getTime()) / 60_000)

  if (diffMinutes < 1) return "Just now"
  if (diffMinutes < 60) return `${diffMinutes}m ago`

  const diffHours = Math.round(diffMinutes / 60)
  if (diffHours < 24) return `${diffHours}h ago`

  const diffDays = Math.round(diffHours / 24)
  if (diffDays < 30) return `${diffDays}d ago`

  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
}

function stageLabel(stage: string): string {
  return stage.replace(/_/g, " ").toLowerCase()
}

function activityLabel(event: { event_type: string; event_metadata: Record<string, unknown> | null }): string {
  if (event.event_type === "PIPELINE_STAGE_CHANGED") {
    const toStage = event.event_metadata?.to_stage
    if (typeof toStage === "string") {
      if (toStage === "HIRED") return "Hired"
      if (toStage === "ASSESSMENT_SENT") return "Assessment sent"
      if (toStage === "INTERVIEW_SCHEDULED") return "Interview scheduled"
      return `Moved to ${stageLabel(toStage)}`
    }
  }
  if (event.event_type === "ARCHIVED") {
    const fromStage = event.event_metadata?.from_stage
    return typeof fromStage === "string" ? `Archived from ${stageLabel(fromStage)}` : "Archived"
  }
  if (event.event_type === "RESTORED") {
    const toStage = event.event_metadata?.to_stage
    return typeof toStage === "string" ? `Restored to ${stageLabel(toStage)}` : "Restored"
  }
  return ACTIVITY_LABELS[event.event_type as keyof typeof ACTIVITY_LABELS] ?? event.event_type
}

function ActivityTab({ candidateId }: ActivityTabProps) {
  const query = useCandidateActivity(candidateId)

  if (query.isPending) {
    return (
      <Stack gap="sm">
        {Array.from({ length: 5 }).map((_, index) => (
          <Skeleton key={index} className="h-12 w-full" />
        ))}
      </Stack>
    )
  }

  if (query.isError) {
    return <DashboardErrorState error={query.error} onRetry={() => query.refetch()} />
  }

  const events = query.data
  if (events.length === 0) {
    return <TableEmptyState title="No activity yet" description="Candidate events will show up here." />
  }

  return (
    <ol className="flex flex-col gap-4" aria-label="Candidate activity timeline">
      {events.map((event) => {
        const isHired = event.event_type === "PIPELINE_STAGE_CHANGED" && event.event_metadata?.to_stage === "HIRED"
        const Icon = isHired ? Trophy : ACTIVITY_ICON[event.event_type]
        return (
          <li key={event.id} className="flex items-start gap-3">
            <span
              className={cn(
                "flex size-8 shrink-0 items-center justify-center rounded-full",
                isHired ? "bg-success/10 text-success-emphasis" : ACTIVITY_ICON_STYLE[event.event_type]
              )}
            >
              <Icon className="size-4" aria-hidden="true" />
            </span>
            <div className="flex flex-col gap-0.5">
              <p className="text-body text-foreground">
                {activityLabel(event)}
                {event.actor && <span className="text-muted-foreground"> · {event.actor.full_name}</span>}
              </p>
              <time dateTime={event.created_at} className="text-caption text-muted-foreground">
                {formatRelativeTime(event.created_at)}
              </time>
            </div>
          </li>
        )
      })}
    </ol>
  )
}

export { ActivityTab }
