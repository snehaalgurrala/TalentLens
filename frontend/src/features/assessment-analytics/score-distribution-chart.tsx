"use client"

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { useChartTheme } from "@/design-system/charts/useChartTheme"
import type { ScoreDistributionBucket } from "@/types"

export interface ScoreDistributionChartProps {
  buckets: ScoreDistributionBucket[]
}

function ScoreDistributionChart({ buckets }: ScoreDistributionChartProps) {
  const { palette, defaults } = useChartTheme()
  const hasData = buckets.some((bucket) => bucket.count > 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Score Distribution</CardTitle>
        <CardDescription>Overall communication score across completed assessments</CardDescription>
      </CardHeader>
      <CardContent>
        {!hasData ? (
          <TableEmptyState
            title="No scored assessments yet"
            description="Distribution appears once candidates complete assessments with a communication score."
          />
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={buckets} margin={{ left: -16 }}>
              <CartesianGrid stroke={defaults.grid.stroke} strokeDasharray={defaults.grid.strokeDasharray} />
              <XAxis
                dataKey="label"
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

export { ScoreDistributionChart }
