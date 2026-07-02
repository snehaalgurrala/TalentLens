import * as React from "react"
import type { LucideIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

export interface DashboardCardProps extends React.ComponentProps<"div"> {
  title: string
  description?: string
  icon?: LucideIcon
  action?: React.ReactNode
}

function DashboardCard({
  title,
  description,
  icon: Icon,
  action,
  className,
  children,
  ...props
}: DashboardCardProps) {
  return (
    <Card data-slot="dashboard-card" className={cn(className)} {...props}>
      <CardHeader>
        <div className="flex items-center gap-2">
          {Icon && (
            <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Icon className="size-4" aria-hidden="true" />
            </span>
          )}
          <CardTitle>{title}</CardTitle>
        </div>
        {description && <CardDescription>{description}</CardDescription>}
        {action && <CardAction>{action}</CardAction>}
      </CardHeader>
      {children && <CardContent>{children}</CardContent>}
    </Card>
  )
}

export { DashboardCard }
