"use client"

import { Briefcase, CheckCircle2, Users } from "lucide-react"

import { useAnimatedNumber } from "@/hooks/use-animated-number"
import { StatisticCard } from "@/components/ui/statistic-card"
import { Grid } from "@/components/layout/grid"
import type { DashboardSummary } from "@/types"

import { MatchScoreCard } from "./match-score-card"

export interface SummaryCardsProps {
  summary: DashboardSummary
}

function AnimatedStatisticCard({
  value,
  ...props
}: Omit<React.ComponentProps<typeof StatisticCard>, "value"> & { value: number }) {
  const animated = useAnimatedNumber(value)
  return <StatisticCard value={Math.round(animated).toLocaleString()} {...props} />
}

function SummaryCards({ summary }: SummaryCardsProps) {
  const activeShare =
    summary.total_campaigns > 0
      ? Math.round((summary.active_campaigns / summary.total_campaigns) * 100)
      : 0

  return (
    <Grid cols={1} colsSm={2} colsLg={4} gap="md">
      <AnimatedStatisticCard
        label="Total Campaigns"
        value={summary.total_campaigns}
        icon={Briefcase}
        trend={
          summary.total_campaigns > 0
            ? { value: activeShare, direction: "neutral", label: "active" }
            : undefined
        }
      />
      <AnimatedStatisticCard label="Candidates" value={summary.total_candidates} icon={Users} />
      <AnimatedStatisticCard
        label="Shortlisted"
        value={summary.shortlisted_candidates}
        icon={CheckCircle2}
      />
      <MatchScoreCard score={summary.average_match_score} />
    </Grid>
  )
}

export { SummaryCards }
