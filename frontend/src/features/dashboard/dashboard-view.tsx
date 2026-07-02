"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Grid } from "@/components/layout/grid"
import { Stack } from "@/components/layout/stack"
import {
  useDashboardActivity,
  useDashboardSummary,
  useProcessingStatus,
  useRecentCampaigns,
  useTopCandidates,
} from "@/hooks"
import { ActivityFeed } from "./activity-feed"
import {
  CampaignActivityChart,
  CandidatesByStatusChart,
  HiringFunnelChart,
  MatchScoreDistributionChart,
  ProcessingQueueChart,
} from "./charts"
import { DashboardErrorState } from "./dashboard-error-state"
import { ChartSkeleton, SummaryCardsSkeleton } from "./dashboard-skeletons"
import { ProcessingStatusCards } from "./processing-status-cards"
import { RecentCampaignsTable } from "./recent-campaigns-table"
import { SummaryCards } from "./summary-cards"
import { TopCandidatesList } from "./top-candidates-list"

const RECENT_CAMPAIGNS_LIMIT = 5
const TOP_CANDIDATES_LIMIT = 6
const ACTIVITY_LIMIT = 12

function DashboardView() {
  const summaryQuery = useDashboardSummary()
  const recentCampaignsQuery = useRecentCampaigns(RECENT_CAMPAIGNS_LIMIT)
  const topCandidatesQuery = useTopCandidates(TOP_CANDIDATES_LIMIT)
  const processingStatusQuery = useProcessingStatus()
  const activityQuery = useDashboardActivity(ACTIVITY_LIMIT)

  return (
    <Stack gap="xl">
      <section aria-label="Summary metrics">
        {summaryQuery.isPending ? (
          <SummaryCardsSkeleton />
        ) : summaryQuery.isError ? (
          <DashboardErrorState error={summaryQuery.error} onRetry={() => summaryQuery.refetch()} />
        ) : (
          <SummaryCards summary={summaryQuery.data} />
        )}
      </section>

      <section aria-label="Charts">
        <Stack gap="md">
          <Grid cols={1} colsLg={2} gap="md">
            {summaryQuery.isPending || processingStatusQuery.isPending ? (
              <ChartSkeleton />
            ) : summaryQuery.isError || processingStatusQuery.isError ? (
              <DashboardErrorState
                error={
                  summaryQuery.error ??
                  processingStatusQuery.error ?? { status: 0, message: "Something went wrong." }
                }
                onRetry={() => {
                  void summaryQuery.refetch()
                  void processingStatusQuery.refetch()
                }}
              />
            ) : (
              <HiringFunnelChart summary={summaryQuery.data} processingStatus={processingStatusQuery.data} />
            )}

            {summaryQuery.isPending ? (
              <ChartSkeleton />
            ) : summaryQuery.isError ? (
              <DashboardErrorState error={summaryQuery.error} onRetry={() => summaryQuery.refetch()} />
            ) : (
              <CandidatesByStatusChart summary={summaryQuery.data} />
            )}

            {recentCampaignsQuery.isPending ? (
              <ChartSkeleton />
            ) : recentCampaignsQuery.isError ? (
              <DashboardErrorState
                error={recentCampaignsQuery.error}
                onRetry={() => recentCampaignsQuery.refetch()}
              />
            ) : (
              <CampaignActivityChart campaigns={recentCampaignsQuery.data} />
            )}

            {processingStatusQuery.isPending ? (
              <ChartSkeleton />
            ) : processingStatusQuery.isError ? (
              <DashboardErrorState
                error={processingStatusQuery.error}
                onRetry={() => processingStatusQuery.refetch()}
              />
            ) : (
              <ProcessingQueueChart status={processingStatusQuery.data} />
            )}
          </Grid>

          {topCandidatesQuery.isPending ? (
            <ChartSkeleton heightClassName="h-56" />
          ) : topCandidatesQuery.isError ? (
            <DashboardErrorState
              error={topCandidatesQuery.error}
              onRetry={() => topCandidatesQuery.refetch()}
            />
          ) : (
            <MatchScoreDistributionChart candidates={topCandidatesQuery.data} />
          )}
        </Stack>
      </section>

      <Grid cols={1} colsLg={3} gap="lg">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Recent Campaigns</CardTitle>
          </CardHeader>
          <CardContent className="px-0">
            {recentCampaignsQuery.isError ? (
              <div className="px-4">
                <DashboardErrorState
                  error={recentCampaignsQuery.error}
                  onRetry={() => recentCampaignsQuery.refetch()}
                />
              </div>
            ) : (
              <RecentCampaignsTable
                campaigns={recentCampaignsQuery.data ?? []}
                isLoading={recentCampaignsQuery.isPending}
              />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Candidates</CardTitle>
          </CardHeader>
          <CardContent>
            {topCandidatesQuery.isError ? (
              <DashboardErrorState
                error={topCandidatesQuery.error}
                onRetry={() => topCandidatesQuery.refetch()}
              />
            ) : (
              <TopCandidatesList
                candidates={topCandidatesQuery.data ?? []}
                isLoading={topCandidatesQuery.isPending}
              />
            )}
          </CardContent>
        </Card>
      </Grid>

      <section aria-label="Processing status">
        <Stack gap="sm">
          <h2 className="text-h5 text-foreground">Processing Status</h2>
          {processingStatusQuery.isPending ? (
            <SummaryCardsSkeleton count={5} />
          ) : processingStatusQuery.isError ? (
            <DashboardErrorState
              error={processingStatusQuery.error}
              onRetry={() => processingStatusQuery.refetch()}
            />
          ) : (
            <ProcessingStatusCards status={processingStatusQuery.data} />
          )}
        </Stack>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {activityQuery.isError ? (
            <DashboardErrorState error={activityQuery.error} onRetry={() => activityQuery.refetch()} />
          ) : (
            <ActivityFeed events={activityQuery.data ?? []} isLoading={activityQuery.isPending} />
          )}
        </CardContent>
      </Card>
    </Stack>
  )
}

export { DashboardView }
