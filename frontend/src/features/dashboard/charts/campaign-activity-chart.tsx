"use client"

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { useChartTheme } from "@/design-system/charts/useChartTheme"
import type { RecentCampaign } from "@/types"

export interface CampaignActivityChartProps {
  campaigns: RecentCampaign[]
}

function truncateLabel(label: string, maxLength = 14): string {
  return label.length > maxLength ? `${label.slice(0, maxLength - 1)}…` : label
}

function CampaignActivityChart({ campaigns }: CampaignActivityChartProps) {
  const { palette, defaults } = useChartTheme()
  const data = [...campaigns].reverse().map((campaign) => ({
    name: truncateLabel(campaign.title),
    fullName: campaign.title,
    candidates: campaign.candidate_count,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>Campaign Activity</CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <TableEmptyState title="No campaigns yet" description="Create a campaign to see candidate activity here." />
        ) : (
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
              <Tooltip
                contentStyle={defaults.tooltip.contentStyle}
                labelStyle={defaults.tooltip.labelStyle}
                labelFormatter={(_, payload) => payload?.[0]?.payload?.fullName ?? ""}
              />
              <Bar dataKey="candidates" name="Candidates" fill={palette[0]} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}

export { CampaignActivityChart }
