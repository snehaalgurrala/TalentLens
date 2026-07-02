import * as React from "react"
import { TrendingDown, TrendingUp, type LucideIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { Card, CardContent } from "@/components/ui/card"

export interface StatisticCardProps extends React.ComponentProps<"div"> {
  label: string
  value: string | number
  icon?: LucideIcon
  trend?: {
    value: number
    direction: "up" | "down" | "neutral"
    label?: string
  }
}

function StatisticCard({
  label,
  value,
  icon: Icon,
  trend,
  className,
  ...props
}: StatisticCardProps) {
  return (
    <Card data-slot="statistic-card" className={cn(className)} {...props}>
      <CardContent className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <span className="text-caption text-muted-foreground">{label}</span>
          <span className="text-h3 font-semibold tabular-nums text-foreground">
            {value}
          </span>
          {trend && (
            <span
              className={cn(
                "inline-flex items-center gap-1 text-caption font-medium",
                trend.direction === "up" && "text-success-emphasis",
                trend.direction === "down" && "text-destructive-emphasis",
                trend.direction === "neutral" && "text-muted-foreground"
              )}
            >
              {trend.direction === "up" && (
                <TrendingUp className="size-3.5" aria-hidden="true" />
              )}
              {trend.direction === "down" && (
                <TrendingDown className="size-3.5" aria-hidden="true" />
              )}
              {trend.value > 0 ? "+" : ""}
              {trend.value}%{trend.label ? ` ${trend.label}` : ""}
            </span>
          )}
        </div>
        {Icon && (
          <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Icon className="size-5" aria-hidden="true" />
          </span>
        )}
      </CardContent>
    </Card>
  )
}

export { StatisticCard }
