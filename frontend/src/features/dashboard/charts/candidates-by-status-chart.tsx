"use client"

import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { useChartTheme } from "@/design-system/charts/useChartTheme"
import type { DashboardSummary } from "@/types"

export interface CandidatesByStatusChartProps {
  summary: DashboardSummary
}

function CandidatesByStatusChart({ summary }: CandidatesByStatusChartProps) {
  const { palette, defaults } = useChartTheme()

  const pendingReview = Math.max(
    summary.total_candidates -
      summary.processing_candidates -
      summary.shortlisted_candidates -
      summary.rejected_candidates,
    0
  )
  const data = [
    { name: "Processing", value: summary.processing_candidates, color: palette[1] },
    { name: "Shortlisted", value: summary.shortlisted_candidates, color: palette[2] },
    { name: "Rejected", value: summary.rejected_candidates, color: palette[3] },
    { name: "Pending Review", value: pendingReview, color: palette[0] },
  ].filter((entry) => entry.value > 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Candidates by Status</CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <TableEmptyState title="No candidates yet" description="Upload resumes to a campaign to see this breakdown." />
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={data} dataKey="value" nameKey="name" innerRadius={60} outerRadius={90} paddingAngle={2}>
                {data.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip contentStyle={defaults.tooltip.contentStyle} labelStyle={defaults.tooltip.labelStyle} />
              <Legend wrapperStyle={{ fontSize: defaults.axis.fontSize }} />
            </PieChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}

export { CandidatesByStatusChart }
