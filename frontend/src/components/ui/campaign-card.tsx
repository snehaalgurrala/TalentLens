import * as React from "react"

import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

export interface CampaignCardProps extends React.ComponentProps<"div"> {
  title: string
  description?: string
  status?: {
    label: string
    variant?: React.ComponentProps<typeof Badge>["variant"]
  }
  applicantCount?: number
  dateRange?: string
  progress?: number
  actions?: React.ReactNode
}

function CampaignCard({
  title,
  description,
  status,
  applicantCount,
  dateRange,
  progress,
  actions,
  className,
  ...props
}: CampaignCardProps) {
  return (
    <Card data-slot="campaign-card" className={cn(className)} {...props}>
      <CardHeader>
        <div className="flex items-center gap-2">
          <CardTitle>{title}</CardTitle>
          {status && (
            <Badge variant={status.variant ?? "default"}>
              {status.label}
            </Badge>
          )}
        </div>
        {description && <CardDescription>{description}</CardDescription>}
        {actions && <CardAction>{actions}</CardAction>}
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {typeof progress === "number" && (
          <div className="flex flex-col gap-1.5">
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
                role="progressbar"
                aria-valuenow={progress}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            </div>
          </div>
        )}
        {(typeof applicantCount === "number" || dateRange) && (
          <div className="flex items-center justify-between text-caption text-muted-foreground">
            {typeof applicantCount === "number" && (
              <span>{applicantCount} applicants</span>
            )}
            {dateRange && <span>{dateRange}</span>}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export { CampaignCard }
