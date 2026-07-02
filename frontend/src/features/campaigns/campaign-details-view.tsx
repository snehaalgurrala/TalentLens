"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Stack } from "@/components/layout/stack"
import { Grid } from "@/components/layout/grid"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { DashboardErrorState } from "@/features/dashboard"
import { useCampaign, useCampaignProcessingStatus, useCampaignSummary } from "@/hooks"
import { formatDate } from "@/utils"

import { CampaignActionsMenu } from "./campaign-actions-menu"
import { CampaignPriorityBadge, CampaignStatusBadge } from "./campaign-badges"
import { CampaignSummaryCards } from "./campaign-summary-cards"
import { CandidateSummaryTable } from "./candidate-summary-table"
import { EMPLOYMENT_TYPE_LABELS } from "./constants"
import { JdPanel } from "./jd-panel"
import { ProcessingMonitor } from "./processing-monitor"
import { ResumeUploadPanel } from "./resume-upload-panel"

export interface CampaignDetailsViewProps {
  campaignId: string
}

function DetailField({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-caption text-muted-foreground">{label}</span>
      <span className="text-sm text-foreground">{value ?? "—"}</span>
    </div>
  )
}

function CampaignDetailsView({ campaignId }: CampaignDetailsViewProps) {
  const campaignQuery = useCampaign(campaignId)
  const summaryQuery = useCampaignSummary(campaignId)
  const processingStatusQuery = useCampaignProcessingStatus(campaignId)

  if (campaignQuery.isPending) {
    return (
      <Stack gap="lg">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-32 w-full" />
      </Stack>
    )
  }

  if (campaignQuery.isError) {
    return <DashboardErrorState error={campaignQuery.error} onRetry={() => campaignQuery.refetch()} />
  }

  const campaign = campaignQuery.data

  return (
    <Stack gap="lg">
      <Card>
        <CardContent className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-h4 text-foreground">{campaign.title}</h2>
              <CampaignStatusBadge status={campaign.status} />
              <CampaignPriorityBadge priority={campaign.priority} />
            </div>
            {campaign.description && (
              <p className="max-w-2xl text-sm text-muted-foreground">{campaign.description}</p>
            )}
          </div>
          <CampaignActionsMenu campaign={campaign} />
        </CardContent>
      </Card>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="job-description">Job Description</TabsTrigger>
          <TabsTrigger value="resumes">Resumes &amp; Processing</TabsTrigger>
          <TabsTrigger value="candidates">Candidates</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="flex flex-col gap-6 pt-4">
          {summaryQuery.isPending || !summaryQuery.data ? (
            <Skeleton className="h-24 w-full" />
          ) : summaryQuery.isError ? (
            <DashboardErrorState error={summaryQuery.error} onRetry={() => summaryQuery.refetch()} />
          ) : (
            <CampaignSummaryCards summary={summaryQuery.data} />
          )}

          <Card>
            <CardHeader>
              <CardTitle>Campaign Details</CardTitle>
            </CardHeader>
            <CardContent>
              <Grid cols={2} colsSm={3} gap="md">
                <DetailField label="Job Title" value={campaign.job_title} />
                <DetailField label="Department" value={campaign.department} />
                <DetailField label="Location" value={campaign.location} />
                <DetailField
                  label="Employment Type"
                  value={campaign.employment_type ? EMPLOYMENT_TYPE_LABELS[campaign.employment_type] : null}
                />
                <DetailField
                  label="Experience"
                  value={
                    campaign.experience_min_years !== null || campaign.experience_max_years !== null
                      ? `${campaign.experience_min_years ?? "?"}–${campaign.experience_max_years ?? "?"} yrs`
                      : null
                  }
                />
                <DetailField
                  label="Salary Range"
                  value={
                    campaign.salary_min !== null || campaign.salary_max !== null
                      ? `${campaign.salary_min?.toLocaleString() ?? "?"} – ${campaign.salary_max?.toLocaleString() ?? "?"}`
                      : null
                  }
                />
                <DetailField label="Openings" value={campaign.openings_count} />
                <DetailField label="Hiring Manager" value={campaign.hiring_manager?.full_name} />
                <DetailField label="Recruiter" value={campaign.recruiter?.full_name} />
                <DetailField
                  label="Closing Date"
                  value={campaign.closing_date ? formatDate(campaign.closing_date) : null}
                />
                <DetailField label="Created" value={formatDate(campaign.created_at)} />
                <DetailField label="Last Updated" value={formatDate(campaign.updated_at)} />
              </Grid>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="job-description" className="pt-4">
          <JdPanel campaignId={campaignId} />
        </TabsContent>

        <TabsContent value="resumes" className="flex flex-col gap-6 pt-4">
          <ProcessingMonitor status={processingStatusQuery.data} isLoading={processingStatusQuery.isPending} />
          <ResumeUploadPanel campaignId={campaignId} />
        </TabsContent>

        <TabsContent value="candidates" className="pt-4">
          <CandidateSummaryTable campaignId={campaignId} />
        </TabsContent>
      </Tabs>
    </Stack>
  )
}

export { CampaignDetailsView }
