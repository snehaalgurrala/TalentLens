"use client"

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { useChartTheme } from "@/design-system/charts/useChartTheme"
import type { CompletionTrendPoint } from "@/types"

export interface CompletionTrendChartProps {
  points: CompletionTrendPoint[]
}

function formatTick(dateIso: string): string {
  return new Date(dateIso).toLocaleDateString(undefined, { month: "short", day: "numeric" })
}

function CompletionTrendChart({ points }: CompletionTrendChartProps) {
  const { palette, defaults } = useChartTheme()
  const hasData = points.some((point) => point.completed_count > 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Completion Trend</CardTitle>
        <CardDescription>Assessments completed per day (last 14 days)</CardDescription>
      </CardHeader>
      <CardContent>
        {!hasData ? (
          <TableEmptyState
            title="No completions yet"
            description="The trend fills in as candidates complete their assessments."
          />
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={points} margin={{ left: -16 }}>
              <CartesianGrid stroke={defaults.grid.stroke} strokeDasharray={defaults.grid.strokeDasharray} />
              <XAxis
                dataKey="date"
                tickFormatter={formatTick}
                tick={{ fontSize: defaults.axis.fontSize, fill: defaults.axis.stroke }}
                stroke={defaults.axis.stroke}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: defaults.axis.fontSize, fill: defaults.axis.stroke }}
                stroke={defaults.axis.stroke}
              />
              <Tooltip
                contentStyle={defaults.tooltip.contentStyle}
                labelStyle={defaults.tooltip.labelStyle}
                labelFormatter={(value) => formatTick(String(value))}
              />
              <Line
                type="monotone"
                dataKey="completed_count"
                name="Completed"
                stroke={palette[0]}
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}

export { CompletionTrendChart }
