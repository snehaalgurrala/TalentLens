import * as React from "react"
import type { LucideIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"

export interface CandidateCardMetaItem {
  icon: LucideIcon
  label: string
}

export interface CandidateCardProps extends React.ComponentProps<"div"> {
  name: string
  role?: string
  avatarUrl?: string
  initials: string
  status?: {
    label: string
    variant?: React.ComponentProps<typeof Badge>["variant"]
  }
  matchScore?: number
  meta?: CandidateCardMetaItem[]
  actions?: React.ReactNode
}

function CandidateCard({
  name,
  role,
  avatarUrl,
  initials,
  status,
  matchScore,
  meta,
  actions,
  className,
  ...props
}: CandidateCardProps) {
  return (
    <Card data-slot="candidate-card" className={cn(className)} {...props}>
      <CardContent className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <Avatar size="lg">
              {avatarUrl && <AvatarImage src={avatarUrl} alt={name} />}
              <AvatarFallback>{initials}</AvatarFallback>
            </Avatar>
            <div className="flex flex-col">
              <span className="text-body font-medium text-foreground">
                {name}
              </span>
              {role && (
                <span className="text-caption text-muted-foreground">
                  {role}
                </span>
              )}
            </div>
          </div>
          {typeof matchScore === "number" && (
            <span className="shrink-0 text-h6 font-semibold tabular-nums text-primary">
              {matchScore}%
            </span>
          )}
        </div>

        {meta && meta.length > 0 && (
          <ul className="flex flex-col gap-1.5">
            {meta.map(({ icon: Icon, label }, index) => (
              <li
                key={index}
                className="flex items-center gap-2 text-caption text-muted-foreground"
              >
                <Icon className="size-3.5 shrink-0" aria-hidden="true" />
                <span className="truncate">{label}</span>
              </li>
            ))}
          </ul>
        )}

        {(status || actions) && (
          <div className="flex items-center justify-between gap-2">
            {status && (
              <Badge variant={status.variant ?? "default"}>
                {status.label}
              </Badge>
            )}
            {actions}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export { CandidateCard }
