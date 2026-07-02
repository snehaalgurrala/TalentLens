"use client"

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useChartTheme } from "@/design-system/charts/useChartTheme"
import type { ProcessingStatus } from "@/types"

export interface ProcessingQueueChartProps {
  status: ProcessingStatus
}

function ProcessingQueueChart({ status }: ProcessingQueueChartProps) {
  const { palette, defaults } = useChartTheme()
  const data = [
    { name: "Parsing", value: status.parsing_queue, color: palette[0] },
    { name: "Embedding", value: status.embedding_queue, color: palette[1] },
    { name: "Ready to Rank", value: status.ranking_queue, color: palette[2] },
    { name: "Completed", value: status.completed_jobs, color: palette[2] },
    { name: "Failed", value: status.failed_jobs, color: palette[3] },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>Processing Queue</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={260}>
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
            <Bar dataKey="value" name="Count" radius={[4, 4, 0, 0]}>
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

export { ProcessingQueueChart }
