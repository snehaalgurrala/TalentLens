"use client"

import { AlertTriangle, CheckCircle2, FileText, Gauge, Layers } from "lucide-react"

import { StatisticCard } from "@/components/ui/statistic-card"
import { Grid } from "@/components/layout/grid"
import type { ProcessingStatus } from "@/types"

export interface ProcessingStatusCardsProps {
  status: ProcessingStatus
}

function ProcessingStatusCards({ status }: ProcessingStatusCardsProps) {
  return (
    <Grid cols={1} colsSm={2} colsLg={4} gap="md" className="xl:grid-cols-5">
      <StatisticCard label="Parsing Queue" value={status.parsing_queue} icon={FileText} />
      <StatisticCard label="Embeddings" value={status.embedding_queue} icon={Layers} />
      <StatisticCard label="Ready to Rank" value={status.ranking_queue} icon={Gauge} />
      <StatisticCard label="Completed" value={status.completed_jobs} icon={CheckCircle2} />
      <StatisticCard label="Failed" value={status.failed_jobs} icon={AlertTriangle} />
    </Grid>
  )
}

export { ProcessingStatusCards }
