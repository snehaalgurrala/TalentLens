"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { LayoutGrid, Plus, RefreshCw, Table as TableIcon } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { SearchInput } from "@/components/ui/search-input"
import { Stack } from "@/components/layout/stack"
import { useCampaigns, useDebouncedValue } from "@/hooks"
import { campaignKeys } from "@/hooks/use-campaigns"
import { campaignService } from "@/services/campaign.service"
import { useQueryClient } from "@tanstack/react-query"
import { downloadCsv, toCsv } from "@/utils"
import type { Campaign, CampaignFilters as CampaignFiltersValue } from "@/types"

import { CampaignsGrid } from "./campaigns-grid"
import { CampaignsTable } from "./campaigns-table"
import { CampaignFilters } from "./campaign-filters"
import { CampaignForm } from "./campaign-form"
import { DashboardErrorState } from "@/features/dashboard"

const PAGE_SIZE = 20
const SEARCH_DEBOUNCE_MS = 350

function CampaignsListView() {
  const router = useRouter()
  const queryClient = useQueryClient()

  const [searchInput, setSearchInput] = React.useState("")
  const debouncedSearch = useDebouncedValue(searchInput, SEARCH_DEBOUNCE_MS)
  const [filters, setFilters] = React.useState<CampaignFiltersValue>({
    skip: 0,
    limit: PAGE_SIZE,
    sort_by: "created_at",
    sort_dir: "desc",
  })
  const [viewMode, setViewMode] = React.useState<"table" | "grid">("table")
  const [selectedIds, setSelectedIds] = React.useState<Set<string>>(new Set())
  const [createOpen, setCreateOpen] = React.useState(false)
  const [isBulkWorking, setIsBulkWorking] = React.useState(false)

  const effectiveFilters = React.useMemo(
    () => ({ ...filters, search: debouncedSearch || undefined }),
    [filters, debouncedSearch]
  )

  const campaignsQuery = useCampaigns(effectiveFilters)
  const campaigns = campaignsQuery.data ?? []
  const hasNextPage = campaigns.length === (filters.limit ?? PAGE_SIZE)
  const currentPage = Math.floor((filters.skip ?? 0) / (filters.limit ?? PAGE_SIZE)) + 1

  function goToPage(page: number) {
    setFilters((prev) => ({ ...prev, skip: Math.max(0, (page - 1) * (prev.limit ?? PAGE_SIZE)) }))
    setSelectedIds(new Set())
  }

  function handleSortChange(key: string) {
    setFilters((prev) => ({
      ...prev,
      sort_by: key as CampaignFiltersValue["sort_by"],
      sort_dir: prev.sort_by === key && prev.sort_dir === "asc" ? "desc" : "asc",
      skip: 0,
    }))
  }

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function toggleSelectAll() {
    setSelectedIds((prev) =>
      campaigns.length > 0 && campaigns.every((c) => prev.has(c.id)) ? new Set() : new Set(campaigns.map((c) => c.id))
    )
  }

  async function handleBulkArchive() {
    setIsBulkWorking(true)
    const results = await Promise.allSettled(
      Array.from(selectedIds).map((id) => campaignService.update(id, { status: "ARCHIVED" }))
    )
    const failed = results.filter((r) => r.status === "rejected").length
    toast[failed > 0 ? "error" : "success"](
      failed > 0
        ? `Archived ${results.length - failed} campaigns, ${failed} failed`
        : `Archived ${results.length} campaigns`
    )
    setSelectedIds(new Set())
    setIsBulkWorking(false)
    void queryClient.invalidateQueries({ queryKey: campaignKeys.all })
  }

  async function handleBulkDelete() {
    setIsBulkWorking(true)
    const results = await Promise.allSettled(
      Array.from(selectedIds).map((id) => campaignService.remove(id))
    )
    const failed = results.filter((r) => r.status === "rejected").length
    toast[failed > 0 ? "error" : "success"](
      failed > 0
        ? `Deleted ${results.length - failed} campaigns, ${failed} failed`
        : `Deleted ${results.length} campaigns`
    )
    setSelectedIds(new Set())
    setIsBulkWorking(false)
    void queryClient.invalidateQueries({ queryKey: campaignKeys.all })
  }

  function handleExportCsv() {
    const csv = toCsv(campaigns, [
      { header: "Campaign Name", value: (c: Campaign) => c.title },
      { header: "Job Title", value: (c: Campaign) => c.job_title },
      { header: "Department", value: (c: Campaign) => c.department },
      { header: "Location", value: (c: Campaign) => c.location },
      { header: "Employment Type", value: (c: Campaign) => c.employment_type },
      { header: "Status", value: (c: Campaign) => c.status },
      { header: "Created Date", value: (c: Campaign) => c.created_at },
      { header: "Resume Count", value: (c: Campaign) => c.resume_count },
    ])
    downloadCsv("campaigns.csv", csv)
  }

  return (
    <Stack gap="lg">
      <Stack direction="row" align="center" justify="between" gap="md" className="flex-wrap">
        <div className="min-w-64 flex-1">
          <SearchInput
            placeholder="Search campaigns..."
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            onClear={() => setSearchInput("")}
          />
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => campaignsQuery.refetch()}>
            <RefreshCw className="size-4" aria-hidden="true" />
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={handleExportCsv} disabled={campaigns.length === 0}>
            Export CSV
          </Button>
          <div className="flex items-center overflow-hidden rounded-lg border border-border">
            <Button
              variant={viewMode === "table" ? "secondary" : "ghost"}
              size="icon-sm"
              className="rounded-none"
              aria-pressed={viewMode === "table"}
              aria-label="Table view"
              onClick={() => setViewMode("table")}
            >
              <TableIcon className="size-4" aria-hidden="true" />
            </Button>
            <Button
              variant={viewMode === "grid" ? "secondary" : "ghost"}
              size="icon-sm"
              className="rounded-none"
              aria-pressed={viewMode === "grid"}
              aria-label="Grid view"
              onClick={() => setViewMode("grid")}
            >
              <LayoutGrid className="size-4" aria-hidden="true" />
            </Button>
          </div>
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="size-4" aria-hidden="true" />
            New Campaign
          </Button>
        </div>
      </Stack>

      <CampaignFilters filters={filters} onChange={setFilters} />

      {selectedIds.size > 0 && (
        <Stack
          direction="row"
          align="center"
          justify="between"
          gap="md"
          className="rounded-lg border border-border bg-muted/50 px-3 py-2"
        >
          <span className="text-sm text-foreground">{selectedIds.size} selected</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleBulkArchive} disabled={isBulkWorking}>
              Archive
            </Button>
            <Button variant="destructive" size="sm" onClick={handleBulkDelete} disabled={isBulkWorking}>
              Delete
            </Button>
          </div>
        </Stack>
      )}

      {campaignsQuery.isError ? (
        <DashboardErrorState error={campaignsQuery.error} onRetry={() => campaignsQuery.refetch()} />
      ) : viewMode === "table" ? (
        <CampaignsTable
          campaigns={campaigns}
          isLoading={campaignsQuery.isPending}
          selectedIds={selectedIds}
          onToggleSelect={toggleSelect}
          onToggleSelectAll={toggleSelectAll}
          onRowClick={(campaign) => router.push(`/campaigns/${campaign.id}`)}
          sortKey={filters.sort_by}
          sortDirection={filters.sort_dir}
          onSortChange={handleSortChange}
        />
      ) : (
        <CampaignsGrid
          campaigns={campaigns}
          isLoading={campaignsQuery.isPending}
          onCardClick={(campaign) => router.push(`/campaigns/${campaign.id}`)}
        />
      )}

      {!campaignsQuery.isError && (campaigns.length > 0 || currentPage > 1) && (
        <Stack direction="row" align="center" justify="between" gap="md">
          <span className="text-caption text-muted-foreground">Page {currentPage}</span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage === 1}
              onClick={() => goToPage(currentPage - 1)}
            >
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={!hasNextPage} onClick={() => goToPage(currentPage + 1)}>
              Next
            </Button>
          </div>
        </Stack>
      )}

      <CampaignForm mode="create" open={createOpen} onOpenChange={setCreateOpen} />
    </Stack>
  )
}

export { CampaignsListView }
