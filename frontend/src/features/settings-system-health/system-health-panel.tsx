"use client"

import * as React from "react"
import { RefreshCw } from "lucide-react"

import { Grid } from "@/components/layout/grid"
import { Stack } from "@/components/layout/stack"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { StatisticCard } from "@/components/ui/statistic-card"
import { DashboardErrorState } from "@/features/dashboard"
import { useSystemHealth } from "@/hooks"

type BadgeVariant = React.ComponentProps<typeof Badge>["variant"]

const STATUS_DISPLAY: Record<string, { variant: BadgeVariant; label: string }> = {
  ok: { variant: "active", label: "OK" },
  loaded: { variant: "active", label: "Loaded" },
  error: { variant: "rejected", label: "Error" },
  down: { variant: "rejected", label: "Down" },
  not_initialized: { variant: "pending", label: "Not Initialized" },
  not_loaded: { variant: "pending", label: "Not Loaded" },
}

function StatusBadge({ status }: { status: string }) {
  const display = STATUS_DISPLAY[status] ?? { variant: "outline" as BadgeVariant, label: status }
  return <Badge variant={display.variant}>{display.label}</Badge>
}

function CheckCard({
  title,
  status,
  extra,
}: {
  title: string
  status: string
  extra?: React.ReactNode
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-2">
          <span>{title}</span>
          <StatusBadge status={status} />
        </CardTitle>
      </CardHeader>
      {extra && <CardContent>{extra}</CardContent>}
    </Card>
  )
}

function SystemHealthPanel() {
  const healthQuery = useSystemHealth()

  if (healthQuery.isPending) {
    return (
      <Stack gap="lg">
        <Grid cols={1} colsSm={2} colsLg={3} gap="md">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-24 w-full" />
          ))}
        </Grid>
        <Skeleton className="h-24 w-full" />
      </Stack>
    )
  }

  if (healthQuery.isError) {
    return <DashboardErrorState error={healthQuery.error} onRetry={() => healthQuery.refetch()} />
  }

  const { checks, environment, version, build, timestamp } = healthQuery.data

  return (
    <Stack gap="lg">
      <div className="flex items-center justify-end">
        <Button
          variant="outline"
          size="sm"
          onClick={() => healthQuery.refetch()}
          isLoading={healthQuery.isRefetching}
        >
          <RefreshCw className="size-3.5" aria-hidden="true" />
          Refresh
        </Button>
      </div>

      <Grid cols={1} colsSm={2} colsLg={3} gap="md">
        <CheckCard title="Database" status={checks.database} />
        <CheckCard title="Redis" status={checks.redis} />
        <CheckCard
          title="Celery Workers"
          status={checks.celery_workers.status}
          extra={
            <p className="text-caption text-muted-foreground">
              {checks.celery_workers.worker_count} worker(s) online
            </p>
          }
        />
        <CheckCard title="Whisper Model" status={checks.whisper_model} />
        <CheckCard title="Storage" status={checks.storage} />
        <StatisticCard label="Queue Length" value={checks.queue_length} />
      </Grid>

      <Card>
        <CardHeader>
          <CardTitle>Disk Usage</CardTitle>
        </CardHeader>
        <CardContent>
          <Stack gap="sm">
            <Progress value={checks.disk.percent_used} />
            <p className="text-caption text-muted-foreground">
              {checks.disk.used_gb.toFixed(1)} GB used of {checks.disk.total_gb.toFixed(1)} GB (
              {checks.disk.percent_used.toFixed(1)}%)
            </p>
          </Stack>
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-x-6 gap-y-1 text-caption text-muted-foreground">
        <span>Environment: {environment}</span>
        <span>Version: {version}</span>
        <span>Build: {build}</span>
        <span>Last updated: {new Date(timestamp).toLocaleString()}</span>
      </div>
    </Stack>
  )
}

export { SystemHealthPanel }
