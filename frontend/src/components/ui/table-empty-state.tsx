import * as React from "react"
import type { LucideIcon } from "lucide-react"
import { Inbox } from "lucide-react"

import { cn } from "@/lib/utils"

export interface TableEmptyStateProps extends React.ComponentProps<"div"> {
  icon?: LucideIcon
  title: string
  description?: string
  action?: React.ReactNode
}

function TableEmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
  ...props
}: TableEmptyStateProps) {
  return (
    <div
      data-slot="table-empty-state"
      className={cn(
        "flex flex-col items-center justify-center gap-3 px-4 py-12 text-center",
        className
      )}
      {...props}
    >
      <span className="flex size-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <Icon className="size-5" aria-hidden="true" />
      </span>
      <div className="flex flex-col gap-1">
        <p className="text-body font-medium text-foreground">{title}</p>
        {description && (
          <p className="text-caption text-muted-foreground">{description}</p>
        )}
      </div>
      {action}
    </div>
  )
}

export { TableEmptyState }
