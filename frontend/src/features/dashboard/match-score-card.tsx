"use client"

import { PolarAngleAxis, RadialBar, RadialBarChart } from "recharts"

import { useAnimatedNumber } from "@/hooks/use-animated-number"
import { Card, CardContent } from "@/components/ui/card"
import { useChartTheme } from "@/design-system/charts/useChartTheme"

export interface MatchScoreCardProps {
  score: number | null
}

function MatchScoreCard({ score }: MatchScoreCardProps) {
  const { palette } = useChartTheme()
  const animated = useAnimatedNumber(score ?? 0)
  const data = [{ name: "score", value: score ?? 0, fill: palette[0] }]

  return (
    <Card data-slot="statistic-card">
      <CardContent className="flex items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <span className="text-caption text-muted-foreground">Average Match Score</span>
          <span className="text-h3 font-semibold tabular-nums text-foreground">
            {score === null ? "—" : `${Math.round(animated)}%`}
          </span>
          {score === null && (
            <span className="text-caption text-muted-foreground">No ranked candidates yet</span>
          )}
        </div>
        <div
          className="relative size-16 shrink-0"
          role="img"
          aria-label={score === null ? "No match score available" : `Average match score ${Math.round(score)}%`}
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
        </div>
      </CardContent>
    </Card>
  )
}

export { MatchScoreCard }
