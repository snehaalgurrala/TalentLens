"use client"

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useChartTheme } from "@/design-system/charts/useChartTheme"
import type { DashboardSummary, ProcessingStatus } from "@/types"

export interface HiringFunnelChartProps {
  summary: DashboardSummary
  processingStatus: ProcessingStatus
}

function HiringFunnelChart({ summary, processingStatus }: HiringFunnelChartProps) {
  const { palette, defaults } = useChartTheme()
  const data = [
    { stage: "Total Candidates", count: summary.total_candidates },
    { stage: "Processing", count: summary.processing_candidates },
    { stage: "Ready to Rank", count: processingStatus.ranking_queue },
    { stage: "Shortlisted", count: summary.shortlisted_candidates },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>Hiring Funnel</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
            <CartesianGrid
              horizontal={false}
              stroke={defaults.grid.stroke}
              strokeDasharray={defaults.grid.strokeDasharray}
            />
            <XAxis
              type="number"
              allowDecimals={false}
              tick={{ fontSize: defaults.axis.fontSize, fill: defaults.axis.stroke }}
              stroke={defaults.axis.stroke}
            />
            <YAxis
              type="category"
              dataKey="stage"
              width={100}
              tick={{ fontSize: defaults.axis.fontSize, fill: defaults.axis.stroke }}
              stroke={defaults.axis.stroke}
            />
            <Tooltip contentStyle={defaults.tooltip.contentStyle} labelStyle={defaults.tooltip.labelStyle} />
            <Bar dataKey="count" name="Candidates" radius={[0, 4, 4, 0]}>
              {data.map((entry, index) => (
                <Cell key={entry.stage} fill={palette[index % palette.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

export { HiringFunnelChart }
