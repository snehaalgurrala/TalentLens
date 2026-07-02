"use client"

import { Checkbox } from "@/components/ui/checkbox"
import { DataTable, type DataTableColumn } from "@/components/ui/data-table"
import { formatDate } from "@/utils"
import type { Campaign } from "@/types"

import { CampaignActionsMenu } from "./campaign-actions-menu"
import { CampaignStatusBadge } from "./campaign-badges"
import { EMPLOYMENT_TYPE_LABELS } from "./constants"

export interface CampaignsTableProps {
  campaigns: Campaign[]
  isLoading: boolean
  selectedIds: Set<string>
  onToggleSelect: (id: string) => void
  onToggleSelectAll: () => void
  onRowClick: (campaign: Campaign) => void
  sortKey?: string
  sortDirection?: "asc" | "desc"
  onSortChange: (key: string) => void
}

function ProcessingBadge({ campaign }: { campaign: Campaign }) {
  if (campaign.resume_count === 0) {
    return <span className="text-caption text-muted-foreground">No resumes</span>
  }
  if (campaign.processing_resume_count > 0) {
    return (
      <span className="text-caption font-medium text-warning-emphasis">
        Processing ({campaign.processing_resume_count})
      </span>
    )
  }
  return <span className="text-caption font-medium text-success-emphasis">Ready</span>
}

function CampaignsTable({
  campaigns,
  isLoading,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onRowClick,
  sortKey,
  sortDirection,
  onSortChange,
}: CampaignsTableProps) {
  const allSelected = campaigns.length > 0 && campaigns.every((c) => selectedIds.has(c.id))

  const columns: DataTableColumn<Campaign>[] = [
    {
      key: "select",
      header: (
        <Checkbox
          checked={allSelected}
          onCheckedChange={onToggleSelectAll}
          aria-label="Select all campaigns"
          onClick={(event) => event.stopPropagation()}
        />
      ),
      render: (campaign) => (
        <Checkbox
          checked={selectedIds.has(campaign.id)}
          onCheckedChange={() => onToggleSelect(campaign.id)}
          onClick={(event) => event.stopPropagation()}
          aria-label={`Select ${campaign.title}`}
        />
      ),
    },
    {
      key: "title",
      header: "Campaign Name",
      sortable: true,
      render: (campaign) => (
        <div className="flex flex-col">
          <span className="font-medium text-foreground">{campaign.title}</span>
          {campaign.job_title && (
            <span className="text-caption text-muted-foreground">{campaign.job_title}</span>
          )}
        </div>
      ),
    },
    {
      key: "department",
      header: "Department",
      render: (campaign) => campaign.department || <span className="text-muted-foreground">—</span>,
    },
    {
      key: "location",
      header: "Location",
      render: (campaign) => campaign.location || <span className="text-muted-foreground">—</span>,
    },
    {
      key: "employment_type",
      header: "Employment Type",
      render: (campaign) =>
        campaign.employment_type ? (
          EMPLOYMENT_TYPE_LABELS[campaign.employment_type]
        ) : (
          <span className="text-muted-foreground">—</span>
        ),
    },
    {
      key: "status",
      header: "Status",
      sortable: true,
      render: (campaign) => <CampaignStatusBadge status={campaign.status} />,
    },
    {
      key: "created_at",
      header: "Created Date",
      sortable: true,
      render: (campaign) => formatDate(campaign.created_at),
    },
    {
      key: "resume_count",
      header: "Resume Count",
      align: "center",
      render: (campaign) => campaign.resume_count,
    },
    {
      key: "processing",
      header: "AI Processing Status",
      render: (campaign) => <ProcessingBadge campaign={campaign} />,
    },
    {
      key: "updated_at",
      header: "Last Updated",
      sortable: true,
      render: (campaign) => formatDate(campaign.updated_at),
    },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (campaign) => (
        <div onClick={(event) => event.stopPropagation()}>
          <CampaignActionsMenu campaign={campaign} />
        </div>
      ),
    },
  ]

  return (
    <DataTable
      columns={columns}
      data={campaigns}
      getRowKey={(campaign) => campaign.id}
      state={isLoading ? "loading" : campaigns.length === 0 ? "empty" : "ready"}
      emptyTitle="No campaigns yet"
      emptyDescription="Create your first campaign to start collecting and ranking candidates."
      sortKey={sortKey}
      sortDirection={sortDirection}
      onSortChange={onSortChange}
      onRowClick={onRowClick}
    />
  )
}

export { CampaignsTable, ProcessingBadge }
