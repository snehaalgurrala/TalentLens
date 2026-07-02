"use client"

import Link from "next/link"
import { Briefcase } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { TableLoadingState } from "@/components/ui/table-loading-state"
import type { CampaignStatus, RecentCampaign } from "@/types"

export interface RecentCampaignsTableProps {
  campaigns: RecentCampaign[]
  isLoading: boolean
}

const STATUS_BADGE_VARIANT: Record<
  CampaignStatus,
  React.ComponentProps<typeof Badge>["variant"]
> = {
  DRAFT: "secondary",
  ACTIVE: "active",
  PAUSED: "pending",
  CLOSED: "outline",
  ARCHIVED: "outline",
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  })
}

function RecentCampaignsTable({ campaigns, isLoading }: RecentCampaignsTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead>Campaign</TableHead>
          <TableHead>Created</TableHead>
          <TableHead>Candidates</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">Action</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {isLoading ? (
          <TableLoadingState columns={5} />
        ) : campaigns.length === 0 ? (
          <TableRow className="hover:bg-transparent">
            <TableCell colSpan={5}>
              <TableEmptyState
                icon={Briefcase}
                title="No campaigns yet"
                description="Create a campaign to start ranking candidates."
              />
            </TableCell>
          </TableRow>
        ) : (
          campaigns.map((campaign) => (
            <TableRow key={campaign.id}>
              <TableCell className="font-medium text-foreground">{campaign.title}</TableCell>
              <TableCell className="text-muted-foreground">{formatDate(campaign.created_at)}</TableCell>
              <TableCell>{campaign.candidate_count}</TableCell>
              <TableCell>
                <Badge variant={STATUS_BADGE_VARIANT[campaign.status]}>{campaign.status}</Badge>
              </TableCell>
              <TableCell className="text-right">
                <Button variant="ghost" size="sm" asChild>
                  <Link href={`/campaigns/${campaign.id}`}>View</Link>
                </Button>
              </TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  )
}

export { RecentCampaignsTable }
