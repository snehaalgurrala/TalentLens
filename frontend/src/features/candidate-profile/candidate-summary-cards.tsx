"use client"

import { PolarAngleAxis, RadialBar, RadialBarChart } from "recharts"

import { Card, CardContent } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { useChartTheme } from "@/design-system/charts/useChartTheme"
import { cn } from "@/lib/utils"
import type { RankingSubScores } from "@/types"

export interface CandidateSummaryCardsProps {
  overallScore: number | null
  subScores: RankingSubScores | null
}

function scoreTone(score: number): string {
  if (score >= 85) return "text-success-emphasis"
  if (score >= 70) return "text-foreground"
  if (score >= 50) return "text-warning-emphasis"
  return "text-destructive-emphasis"
}

const SUB_SCORE_FIELDS: [key: keyof RankingSubScores, label: string][] = [
  ["semantic_score", "Semantic Score"],
  ["skills_score", "Skills Score"],
  ["experience_score", "Experience Score"],
  ["education_score", "Education Score"],
  ["projects_score", "Projects Score"],
  ["certification_score", "Certifications Score"],
]

function OverallScoreRing({ score }: { score: number }) {
  const { palette } = useChartTheme()
  const data = [{ name: "score", value: score, fill: palette[0] }]

  return (
    <div
      className="relative size-16 shrink-0"
      role="img"
      aria-label={`Overall match score ${score}%`}
    >
      <RadialBarChart
        width={64}
        height={64}
        innerRadius="70%"
        outerRadius="100%"
        data={data}
        startAngle={90}
        endAngle={-270}
      >
        <PolarAngleAxis type="number" domain={[0, 100]} tick={false} axisLine={false} />
        <RadialBar dataKey="value" cornerRadius={8} background={{ fill: "var(--muted)" }} />
      </RadialBarChart>
      <span className="absolute inset-0 flex items-center justify-center text-sm font-semibold tabular-nums text-foreground">
        {score}%
      </span>
    </div>
  )
}

function CandidateSummaryCards({ overallScore, subScores }: CandidateSummaryCardsProps) {
  if (overallScore === null || subScores === null) {
    return (
      <Card>
        <CardContent className="text-sm text-muted-foreground">
          This candidate hasn&rsquo;t been ranked yet — scores appear once the campaign&rsquo;s job
          description finishes parsing and this resume finishes parsing/embedding.
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-7">
      <Card className="col-span-2 sm:col-span-1 lg:col-span-1">
        <CardContent className="flex flex-col items-center justify-center gap-2 text-center">
          <OverallScoreRing score={overallScore} />
          <span className="text-caption text-muted-foreground">Overall Match</span>
        </CardContent>
      </Card>
      {SUB_SCORE_FIELDS.map(([key, label]) => {
        const value = subScores[key]
        return (
          <Card key={key}>
            <CardContent className="flex flex-col gap-2">
              <span className="text-caption text-muted-foreground">{label}</span>
              <span className={cn("text-h6 font-semibold tabular-nums", scoreTone(value))}>
                {value}%
              </span>
              <Progress value={value} className="h-1.5" />
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}

export { CandidateSummaryCards }
