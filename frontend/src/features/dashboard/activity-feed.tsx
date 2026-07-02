"use client"

import { Briefcase, CheckCircle2, UploadCloud, XCircle, type LucideIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { Stack } from "@/components/layout/stack"
import type { DashboardActivityItem, DashboardActivityType } from "@/types"

export interface ActivityFeedProps {
  events: DashboardActivityItem[]
  isLoading: boolean
}

const ACTIVITY_ICON: Record<DashboardActivityType, LucideIcon> = {
  CAMPAIGN_CREATED: Briefcase,
  RESUME_UPLOADED: UploadCloud,
  CANDIDATE_SHORTLISTED: CheckCircle2,
  CANDIDATE_REJECTED: XCircle,
}

const ACTIVITY_ICON_STYLE: Record<DashboardActivityType, string> = {
  CAMPAIGN_CREATED: "bg-primary/10 text-primary",
  RESUME_UPLOADED: "bg-secondary text-secondary-foreground",
  CANDIDATE_SHORTLISTED: "bg-success/10 text-success-emphasis",
  CANDIDATE_REJECTED: "bg-destructive/10 text-destructive-emphasis",
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

function ActivityFeed({ events, isLoading }: ActivityFeedProps) {
  if (isLoading) {
    return (
      <Stack gap="sm">
        {Array.from({ length: 5 }).map((_, index) => (
          <Skeleton key={index} className="h-12 w-full" />
        ))}
      </Stack>
    )
  }

  if (events.length === 0) {
    return (
      <TableEmptyState
        title="No activity yet"
        description="Creating campaigns and uploading resumes will show up here."
      />
    )
  }

  return (
    <ol className="flex flex-col gap-4" aria-label="Recent activity">
      {events.map((event) => {
        const Icon = ACTIVITY_ICON[event.type]
        return (
          <li key={event.id} className="flex items-start gap-3">
            <span
              className={cn(
                "flex size-8 shrink-0 items-center justify-center rounded-full",
                ACTIVITY_ICON_STYLE[event.type]
              )}
            >
              <Icon className="size-4" aria-hidden="true" />
            </span>
            <div className="flex flex-col gap-0.5">
              <p className="text-body text-foreground">{event.description}</p>
              <time dateTime={event.occurred_at} className="text-caption text-muted-foreground">
                {formatRelativeTime(event.occurred_at)}
              </time>
            </div>
          </li>
        )
      })}
    </ol>
  )
}

export { ActivityFeed }
