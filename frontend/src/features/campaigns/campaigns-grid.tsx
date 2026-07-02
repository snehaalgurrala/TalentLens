"use client"

import { Badge } from "@/components/ui/badge"
import { CampaignCard } from "@/components/ui/campaign-card"
import { Grid } from "@/components/layout/grid"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { Skeleton } from "@/components/ui/skeleton"
import { formatDate } from "@/utils"
import type { Campaign, CampaignStatus } from "@/types"

import { CampaignActionsMenu } from "./campaign-actions-menu"
import { CAMPAIGN_STATUS_LABELS } from "./constants"

export interface CampaignsGridProps {
  campaigns: Campaign[]
  isLoading: boolean
  onCardClick: (campaign: Campaign) => void
}

const STATUS_VARIANT: Record<CampaignStatus, React.ComponentProps<typeof Badge>["variant"]> = {
  DRAFT: "secondary",
  ACTIVE: "active",
  PAUSED: "pending",
  CLOSED: "outline",
  ARCHIVED: "outline",
}

function CampaignsGrid({ campaigns, isLoading, onCardClick }: CampaignsGridProps) {
  if (isLoading) {
    return (
      <Grid cols={1} colsSm={2} colsLg={3} gap="md">
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-40 rounded-xl" />
        ))}
      </Grid>
    )
  }

  if (campaigns.length === 0) {
    return (
      <TableEmptyState
        title="No campaigns yet"
        description="Create your first campaign to start collecting and ranking candidates."
      />
    )
  }

  return (
    <Grid cols={1} colsSm={2} colsLg={3} gap="md">
      {campaigns.map((campaign) => (
        <CampaignCard
          key={campaign.id}
          title={campaign.title}
          description={campaign.job_title ?? campaign.description ?? undefined}
          status={{ label: CAMPAIGN_STATUS_LABELS[campaign.status], variant: STATUS_VARIANT[campaign.status] }}
          applicantCount={campaign.resume_count}
          dateRange={formatDate(campaign.created_at)}
          className="cursor-pointer"
          onClick={() => onCardClick(campaign)}
          actions={
            <div onClick={(event) => event.stopPropagation()}>
              <CampaignActionsMenu campaign={campaign} />
            </div>
          }
        />
      ))}
    </Grid>
  )
}

export { CampaignsGrid }
