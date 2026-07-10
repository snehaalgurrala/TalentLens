"use client"

import { CheckCircle2, MessageSquare, Send, Users } from "lucide-react"

import { Grid } from "@/components/layout/grid"
import { Stack } from "@/components/layout/stack"
import { StatisticCard } from "@/components/ui/statistic-card"
import { ChartSkeleton, DashboardErrorState, SummaryCardsSkeleton } from "@/features/dashboard"
import { useAssessmentAnalytics } from "@/hooks"

import { CompletionTrendChart } from "./completion-trend-chart"
import { PerformersList } from "./performers-list"
import { ScoreDistributionChart } from "./score-distribution-chart"

function AssessmentAnalyticsView() {
  const analyticsQuery = useAssessmentAnalytics()

  if (analyticsQuery.isPending) {
    return (
      <Stack gap="lg">
        <SummaryCardsSkeleton count={4} />
        <Grid cols={1} colsLg={2} gap="md">
          <ChartSkeleton />
          <ChartSkeleton />
        </Grid>
      </Stack>
    )
  }

  if (analyticsQuery.isError) {
    return <DashboardErrorState error={analyticsQuery.error} onRetry={() => analyticsQuery.refetch()} />
  }

  const analytics = analyticsQuery.data

  return (
    <Stack gap="lg">
      <Grid cols={1} colsSm={2} colsLg={4} gap="md">
        <StatisticCard
          label="Total Assessments"
          value={analytics.total_sessions}
          icon={Users}
          trend={{
            value: analytics.completion_rate,
            direction: "neutral",
            label: "completed",
          }}
        />
        <StatisticCard label="Completed" value={analytics.completed_sessions} icon={CheckCircle2} />
        <StatisticCard
          label="Avg. Communication Score"
          value={
            analytics.average_communication_score === null
              ? "—"
              : `${analytics.average_communication_score}%`
          }
          icon={MessageSquare}
        />
        <StatisticCard
          label={`Invitation Acceptance Rate (${analytics.invitations_accepted} of ${analytics.total_invitations_sent} sent)`}
          value={`${analytics.invitation_acceptance_rate}%`}
          icon={Send}
        />
      </Grid>

      <Grid cols={1} colsLg={2} gap="md">
        <ScoreDistributionChart buckets={analytics.score_distribution} />
        <CompletionTrendChart points={analytics.completion_trend} />
      </Grid>

      <Grid cols={1} colsLg={2} gap="md">
        <PerformersList
          title="Top Performers"
          description="Highest overall communication scores"
          performers={analytics.top_performers}
          scoreTone="success"
        />
        <PerformersList
          title="Lowest Performers"
          description="Lowest overall communication scores"
          performers={analytics.lowest_performers}
          scoreTone="destructive"
        />
      </Grid>
    </Stack>
  )
}

export { AssessmentAnalyticsView }
