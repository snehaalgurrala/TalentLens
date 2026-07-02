import { CheckCircle2, Loader2, Star, ThumbsDown, ThumbsUp, Users } from "lucide-react"

import { Grid } from "@/components/layout/grid"
import { StatisticCard } from "@/components/ui/statistic-card"
import type { CampaignSummary } from "@/types"

export interface CampaignSummaryCardsProps {
  summary: CampaignSummary
}

function CampaignSummaryCards({ summary }: CampaignSummaryCardsProps) {
  return (
    <Grid cols={2} colsSm={3} colsLg={6} gap="md">
      <StatisticCard label="Total Candidates" value={summary.total_candidates} icon={Users} />
      <StatisticCard label="Processing" value={summary.processing_candidates} icon={Loader2} />
      <StatisticCard label="Ranked" value={summary.ranked_candidates} icon={CheckCircle2} />
      <StatisticCard label="Shortlisted" value={summary.shortlisted_candidates} icon={ThumbsUp} />
      <StatisticCard label="Rejected" value={summary.rejected_candidates} icon={ThumbsDown} />
      <StatisticCard
        label="Avg. Match Score"
        value={summary.average_match_score !== null ? `${summary.average_match_score}%` : "—"}
        icon={Star}
      />
    </Grid>
  )
}

export { CampaignSummaryCards }
