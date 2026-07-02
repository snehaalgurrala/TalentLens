"use client"

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardHeader, CardDescription, CardTitle } from "@/components/ui/card"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { useChartTheme } from "@/design-system/charts/useChartTheme"
import type { TopCandidate } from "@/types"

export interface MatchScoreDistributionChartProps {
  candidates: TopCandidate[]
}

const BUCKETS = [
  { label: "0-19", min: 0, max: 20 },
  { label: "20-39", min: 20, max: 40 },
  { label: "40-59", min: 40, max: 60 },
  { label: "60-79", min: 60, max: 80 },
  { label: "80-100", min: 80, max: 101 },
]

function MatchScoreDistributionChart({ candidates }: MatchScoreDistributionChartProps) {
  const { palette, defaults } = useChartTheme()
  const data = BUCKETS.map((bucket) => ({
    name: bucket.label,
    count: candidates.filter((c) => c.match_score >= bucket.min && c.match_score < bucket.max).length,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>Match Score Distribution</CardTitle>
        <CardDescription>Across the current top-ranked candidates</CardDescription>
      </CardHeader>
      <CardContent>
        {candidates.length === 0 ? (
          <TableEmptyState
            title="No ranked candidates yet"
            description="Score distribution appears once candidates have been ranked against a job description."
          />
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data} margin={{ left: -16 }}>
              <CartesianGrid stroke={defaults.grid.stroke} strokeDasharray={defaults.grid.strokeDasharray} />
              <XAxis
                dataKey="name"
                tick={{ fontSize: defaults.axis.fontSize, fill: defaults.axis.stroke }}
                stroke={defaults.axis.stroke}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: defaults.axis.fontSize, fill: defaults.axis.stroke }}
                stroke={defaults.axis.stroke}
              />
              <Tooltip contentStyle={defaults.tooltip.contentStyle} labelStyle={defaults.tooltip.labelStyle} />
              <Bar dataKey="count" name="Candidates" fill={palette[1]} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}

export { MatchScoreDistributionChart }
