import { Badge } from "@/components/ui/badge"
import type { CampaignPriority, CampaignStatus } from "@/types"

import { CAMPAIGN_PRIORITY_LABELS, CAMPAIGN_STATUS_LABELS } from "./constants"

const STATUS_BADGE_VARIANT: Record<CampaignStatus, React.ComponentProps<typeof Badge>["variant"]> = {
  DRAFT: "secondary",
  ACTIVE: "active",
  PAUSED: "pending",
  CLOSED: "outline",
  ARCHIVED: "outline",
}

const PRIORITY_BADGE_VARIANT: Record<CampaignPriority, React.ComponentProps<typeof Badge>["variant"]> = {
  LOW: "outline",
  MEDIUM: "secondary",
  HIGH: "warning",
  URGENT: "destructive",
}

function CampaignStatusBadge({ status }: { status: CampaignStatus }) {
  return <Badge variant={STATUS_BADGE_VARIANT[status]}>{CAMPAIGN_STATUS_LABELS[status]}</Badge>
}

function CampaignPriorityBadge({ priority }: { priority: CampaignPriority }) {
  return (
    <Badge variant={PRIORITY_BADGE_VARIANT[priority]}>{CAMPAIGN_PRIORITY_LABELS[priority]}</Badge>
  )
}

export { CampaignPriorityBadge, CampaignStatusBadge }
