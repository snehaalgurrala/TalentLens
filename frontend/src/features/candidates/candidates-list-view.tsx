"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { LayoutGrid, List } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Stack } from "@/components/layout/stack"
import { useCampaignCandidates, useCampaigns, useDebouncedValue } from "@/hooks"
import { DashboardErrorState } from "@/features/dashboard"
import { downloadCsv, toCsv } from "@/utils"
import type { CandidateListFilters, CandidateListItem } from "@/types"

import { CandidateNotesDialog } from "./candidate-notes-dialog"
import { CandidatesBulkActionBar } from "./candidates-bulk-action-bar"
import { CandidatesMobileCards } from "./candidates-mobile-card"
import { CandidatesTable } from "./candidates-table"
import { CandidatesToolbar } from "./candidates-toolbar"
import { TERMINAL_STAGES } from "./constants"

const PAGE_SIZE = 20
const SEARCH_DEBOUNCE_MS = 350
const SELECTED_CAMPAIGN_STORAGE_KEY = "tl_candidates_selected_campaign"

function CandidatesListView() {
  const router = useRouter()
  const [selectedCampaignId, setSelectedCampaignId] = React.useState<string | null>(() => {
    if (typeof window === "undefined") return null
    return window.sessionStorage.getItem(SELECTED_CAMPAIGN_STORAGE_KEY)
  })
  const [searchInput, setSearchInput] = React.useState("")
  const debouncedSearch = useDebouncedValue(searchInput, SEARCH_DEBOUNCE_MS)
  const [filters, setFilters] = React.useState<CandidateListFilters>({
    skip: 0,
    limit: PAGE_SIZE,
    sort_by: "overall_score",
    sort_dir: "desc",
  })
  const [selectedIds, setSelectedIds] = React.useState<Set<string>>(new Set())
  const [filterDrawerOpen, setFilterDrawerOpen] = React.useState(false)
  const [notesCandidate, setNotesCandidate] = React.useState<CandidateListItem | null>(null)

  const campaignsQuery = useCampaigns({ sort_by: "updated_at", sort_dir: "desc", limit: 100 })
  const campaignsData = campaignsQuery.data
  const campaigns = campaignsData ?? []

  React.useEffect(() => {
    if (selectedCampaignId || !campaignsData || campaignsData.length === 0) return
    const defaultCampaign = campaignsData.find((c) => c.status !== "ARCHIVED") ?? campaignsData[0]
    setSelectedCampaignId(defaultCampaign.id)
  }, [campaignsData, selectedCampaignId])

  function handleCampaignChange(campaignId: string) {
    setSelectedCampaignId(campaignId)
    window.sessionStorage.setItem(SELECTED_CAMPAIGN_STORAGE_KEY, campaignId)
    setSelectedIds(new Set())
    setFilters((prev) => ({ ...prev, skip: 0 }))
  }

  const effectiveFilters = React.useMemo(
    () => ({ ...filters, search: debouncedSearch || undefined }),
    [filters, debouncedSearch]
  )

  const candidatesQuery = useCampaignCandidates(selectedCampaignId ?? undefined, effectiveFilters)
  const candidates = candidatesQuery.data?.items ?? []
  const total = candidatesQuery.data?.total ?? 0
  const rankingAvailable = candidatesQuery.data?.ranking_available ?? true
  const limit = filters.limit ?? PAGE_SIZE
  const currentPage = Math.floor((filters.skip ?? 0) / limit) + 1
  const totalPages = Math.max(1, Math.ceil(total / limit))

  function goToPage(page: number) {
    setFilters((prev) => ({ ...prev, skip: Math.max(0, (page - 1) * limit) }))
    setSelectedIds(new Set())
  }

  function handleSortChange(key: string) {
    setFilters((prev) => ({
      ...prev,
      sort_by: key as CandidateListFilters["sort_by"],
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
      candidates.length > 0 && candidates.every((c) => prev.has(c.resume_file_id))
        ? new Set()
        : new Set(candidates.map((c) => c.resume_file_id))
    )
  }

  function handleExportCsv() {
    const csv = toCsv(candidates, [
      { header: "Candidate", value: (c: CandidateListItem) => c.candidate_name },
      { header: "Email", value: (c: CandidateListItem) => c.email },
      { header: "Phone", value: (c: CandidateListItem) => c.phone },
      { header: "Current Company", value: (c: CandidateListItem) => c.current_company },
      { header: "Current Role", value: (c: CandidateListItem) => c.current_role },
      { header: "Experience (yrs)", value: (c: CandidateListItem) => c.years_of_experience },
      { header: "Skills", value: (c: CandidateListItem) => c.skills.join("; ") },
      { header: "Match Score", value: (c: CandidateListItem) => c.overall_score },
      { header: "Recommendation", value: (c: CandidateListItem) => c.recommendation },
      { header: "Resume Status", value: (c: CandidateListItem) => c.review_status },
      { header: "Pipeline Stage", value: (c: CandidateListItem) => c.pipeline_stage },
      { header: "Recruiter", value: (c: CandidateListItem) => c.assigned_recruiter?.full_name },
      { header: "Uploaded Date", value: (c: CandidateListItem) => c.applied_at },
    ])
    downloadCsv("candidates.csv", csv)
    toast.success(`Exported ${candidates.length} candidate(s)`)
  }

  return (
    <Stack gap="lg">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <CandidatesToolbar
          campaigns={campaigns}
          selectedCampaignId={selectedCampaignId}
          onCampaignChange={handleCampaignChange}
          searchInput={searchInput}
          onSearchChange={setSearchInput}
          filters={filters}
          onFiltersChange={setFilters}
          filterDrawerOpen={filterDrawerOpen}
          onFilterDrawerOpenChange={setFilterDrawerOpen}
          onRefresh={() => candidatesQuery.refetch()}
          onExportCsv={handleExportCsv}
          exportDisabled={candidates.length === 0}
        />
        <div className="flex items-center gap-2">
          <Button variant="default" size="sm" disabled>
            <List className="size-3.5" aria-hidden="true" />
            Table
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link href="/candidates/board">
              <LayoutGrid className="size-3.5" aria-hidden="true" />
              Board
            </Link>
          </Button>
        </div>
      </div>

      {!rankingAvailable && selectedCampaignId && (
        <div className="rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-sm text-warning-emphasis">
          Add and parse a job description for this campaign to see AI match scores and recommendations.
        </div>
      )}

      {selectedIds.size > 0 && (
        <CandidatesBulkActionBar
          selectedIds={Array.from(selectedIds)}
          onClear={() => setSelectedIds(new Set())}
          showRestore={
            candidates.length > 0 &&
            candidates
              .filter((c) => selectedIds.has(c.resume_file_id))
              .every((c) => TERMINAL_STAGES.has(c.pipeline_stage))
          }
        />
      )}

      {campaignsQuery.isSuccess && campaigns.length === 0 ? (
        <div className="rounded-lg border border-border px-4 py-8 text-center text-sm text-muted-foreground">
          No campaigns yet. Create a campaign and upload resumes to start reviewing candidates.
        </div>
      ) : candidatesQuery.isError ? (
        <DashboardErrorState error={candidatesQuery.error} onRetry={() => candidatesQuery.refetch()} />
      ) : (
        <>
          <div className="hidden md:block">
            <CandidatesTable
              candidates={candidates}
              isLoading={candidatesQuery.isPending}
              rankingAvailable={rankingAvailable}
              selectedIds={selectedIds}
              onToggleSelect={toggleSelect}
              onToggleSelectAll={toggleSelectAll}
              onEditNotes={setNotesCandidate}
              onRowClick={(candidate) => router.push(`/candidates/${candidate.candidate_id}`)}
              sortKey={filters.sort_by}
              sortDirection={filters.sort_dir}
              onSortChange={handleSortChange}
            />
          </div>
          <CandidatesMobileCards
            candidates={candidates}
            selectedIds={selectedIds}
            onToggleSelect={toggleSelect}
            onEditNotes={setNotesCandidate}
          />
        </>
      )}

      {!candidatesQuery.isError && total > 0 && (
        <Stack direction="row" align="center" justify="between" gap="md">
          <span className="text-caption text-muted-foreground">
            Page {currentPage} of {totalPages} · {total} candidate(s)
          </span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={currentPage <= 1} onClick={() => goToPage(currentPage - 1)}>
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage >= totalPages}
              onClick={() => goToPage(currentPage + 1)}
            >
              Next
            </Button>
          </div>
        </Stack>
      )}

      <CandidateNotesDialog candidate={notesCandidate} onOpenChange={(open) => !open && setNotesCandidate(null)} />
    </Stack>
  )
}

export { CandidatesListView }
