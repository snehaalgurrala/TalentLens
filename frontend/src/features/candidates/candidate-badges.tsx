import { Badge } from "@/components/ui/badge"
import type { PipelineStage, RankingRecommendation } from "@/types"

import { PIPELINE_STAGE_LABELS, PIPELINE_STAGE_VARIANT, RECOMMENDATION_VARIANT } from "./constants"

function PipelineStageBadge({ stage }: { stage: PipelineStage }) {
  return <Badge variant={PIPELINE_STAGE_VARIANT[stage]}>{PIPELINE_STAGE_LABELS[stage]}</Badge>
}

function RecommendationBadge({ recommendation }: { recommendation: RankingRecommendation | null }) {
  if (!recommendation) {
    return <span className="text-muted-foreground">—</span>
  }
  return <Badge variant={RECOMMENDATION_VARIANT[recommendation]}>{recommendation}</Badge>
}

export { PipelineStageBadge, RecommendationBadge }
