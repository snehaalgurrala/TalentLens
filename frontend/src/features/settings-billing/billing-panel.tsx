"use client"

import { AlertTriangle } from "lucide-react"

import { Grid } from "@/components/layout/grid"
import { Stack } from "@/components/layout/stack"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { StatisticCard } from "@/components/ui/statistic-card"
import { FEATURES } from "@/config/features"
import { DashboardErrorState } from "@/features/dashboard"
import { useBillingUsage } from "@/hooks"

function formatStorage(mb: number) {
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`
  return `${mb.toFixed(0)} MB`
}

function ComingSoonBanner() {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-dashed border-border bg-muted/50 px-3 py-2 text-caption text-muted-foreground">
      <AlertTriangle className="size-4 shrink-0" aria-hidden="true" />
      <span>Billing integration coming in Phase 7</span>
    </div>
  )
}

function BillingPanel() {
  const usageQuery = useBillingUsage()

  if (usageQuery.isPending) {
    return (
      <Stack gap="lg">
        <Grid cols={1} colsSm={2} colsLg={4} gap="md">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-24 w-full" />
          ))}
        </Grid>
        <Skeleton className="h-40 w-full" />
      </Stack>
    )
  }

  if (usageQuery.isError) {
    return <DashboardErrorState error={usageQuery.error} onRetry={() => usageQuery.refetch()} />
  }

  const usage = usageQuery.data

  return (
    <Stack gap="lg">
      <p className="text-caption text-muted-foreground">
        Usage period: {new Date(usage.period_start).toLocaleDateString()} –{" "}
        {new Date(usage.period_end).toLocaleDateString()}
      </p>

      <Grid cols={1} colsSm={2} colsLg={4} gap="md">
        <StatisticCard label="Users" value={usage.users_count} />
        <StatisticCard label="Storage Used" value={formatStorage(usage.storage_used_mb)} />
        <StatisticCard label="Assessments Used" value={usage.assessments_used} />
        <StatisticCard label="Embedding/Matching Operations" value={usage.embedding_operations_count} />
      </Grid>

      {!FEATURES.billingPaymentsEnabled && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between gap-2">
                <span>Current Plan</span>
                <Badge variant="secondary">{usage.plan_name}</Badge>
              </CardTitle>
              <CardDescription>Plan and payment management is not yet available.</CardDescription>
            </CardHeader>
            <CardContent>
              <Stack gap="sm">
                <ComingSoonBanner />
                <Button disabled className="w-fit">
                  Upgrade Plan
                </Button>
              </Stack>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Invoice History</CardTitle>
              <CardDescription>Past invoices will appear here once billing is enabled.</CardDescription>
            </CardHeader>
            <CardContent>
              <ComingSoonBanner />
            </CardContent>
          </Card>
        </>
      )}
    </Stack>
  )
}

export { BillingPanel }
