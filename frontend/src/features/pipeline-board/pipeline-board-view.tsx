"use client"

import * as React from "react"
import Link from "next/link"
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core"
import { LayoutGrid, List } from "lucide-react"
import { toast } from "sonner"
import { useQueryClient } from "@tanstack/react-query"

import { Button } from "@/components/ui/button"
import { Stack } from "@/components/layout/stack"
import { DashboardErrorState } from "@/features/dashboard"
import {
  CandidateNotesDialog,
  CandidatesBulkActionBar,
  CandidatesToolbar,
  TERMINAL_STAGES,
} from "@/features/candidates"
import {
  candidateManagementKeys,
  useCampaignCandidates,
  useCampaigns,
  useDebouncedValue,
  usePermissions,
  useUpdatePipelineStage,
} from "@/hooks"
import type { CandidateListFilters, CandidateListItem, CandidateListResponse } from "@/types"

import { columnForStage, PIPELINE_BOARD_COLUMNS, TERMINAL_BOARD_COLUMNS } from "./constants"
import { PipelineBoardColumnView } from "./pipeline-board-column"
import { RecruiterWorkloadPanel } from "./recruiter-workload-panel"

const SEARCH_DEBOUNCE_MS = 350
const SELECTED_CAMPAIGN_STORAGE_KEY = "tl_candidates_selected_campaign"
const BOARD_FETCH_LIMIT = 1000

function PipelineBoardView() {
  const queryClient = useQueryClient()
  const { hasAnyRole } = usePermissions()

  const [selectedCampaignId, setSelectedCampaignId] = React.useState<string | null>(() => {
    if (typeof window === "undefined") return null
    return window.sessionStorage.getItem(SELECTED_CAMPAIGN_STORAGE_KEY)
  })
  const [searchInput, setSearchInput] = React.useState("")
  const debouncedSearch = useDebouncedValue(searchInput, SEARCH_DEBOUNCE_MS)
  const [filters, setFilters] = React.useState<CandidateListFilters>({
    skip: 0,
    limit: BOARD_FETCH_LIMIT,
  })
  const [selectedIds, setSelectedIds] = React.useState<Set<string>>(new Set())
  const [filterDrawerOpen, setFilterDrawerOpen] = React.useState(false)
  const [notesCandidate, setNotesCandidate] = React.useState<CandidateListItem | null>(null)
  const [terminalExpanded, setTerminalExpanded] = React.useState(false)

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
  }

  const effectiveFilters = React.useMemo(
    () => ({ ...filters, search: debouncedSearch || undefined }),
    [filters, debouncedSearch]
  )

  const candidatesQuery = useCampaignCandidates(selectedCampaignId ?? undefined, effectiveFilters)
  const candidates = React.useMemo(() => candidatesQuery.data?.items ?? [], [candidatesQuery.data])

  const updatePipelineStage = useUpdatePipelineStage()

  const columns = React.useMemo(() => {
    const byColumn = new Map<string, CandidateListItem[]>()
    for (const column of [...PIPELINE_BOARD_COLUMNS, ...TERMINAL_BOARD_COLUMNS]) {
      byColumn.set(column.key, [])
    }
    for (const candidate of candidates) {
      const column = columnForStage(candidate.pipeline_stage)
      if (column) byColumn.get(column.key)?.push(candidate)
    }
    return byColumn
  }, [candidates])

  const terminalCount = TERMINAL_BOARD_COLUMNS.reduce(
    (sum, col) => sum + (columns.get(col.key)?.length ?? 0),
    0
  )

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor)
  )

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (!over) return
    const candidate = active.data.current?.candidate as CandidateListItem | undefined
    const targetColumn = [...PIPELINE_BOARD_COLUMNS, ...TERMINAL_BOARD_COLUMNS].find(
      (c) => c.key === over.id
    )
    if (!candidate || !targetColumn) return
    if (candidate.pipeline_stage === targetColumn.targetStage) return

    const previousStage = candidate.pipeline_stage
    const queryKey = candidateManagementKeys.list(selectedCampaignId ?? "", effectiveFilters)
    const snapshot = queryClient.getQueryData<CandidateListResponse>(queryKey)

    if (snapshot) {
      queryClient.setQueryData<CandidateListResponse>(queryKey, {
        ...snapshot,
        items: snapshot.items.map((item) =>
          item.resume_file_id === candidate.resume_file_id
            ? { ...item, pipeline_stage: targetColumn.targetStage }
            : item
        ),
      })
    }

    updatePipelineStage.mutate(
      { resumeFileId: candidate.resume_file_id, pipelineStage: targetColumn.targetStage },
      {
        onSuccess: () => {
          toast.success(`Moved to ${targetColumn.label}`, {
            action: {
              label: "Undo",
              onClick: () =>
                updatePipelineStage.mutate({
                  resumeFileId: candidate.resume_file_id,
                  pipelineStage: previousStage,
                }),
            },
          })
        },
        onError: (error) => {
          if (snapshot) queryClient.setQueryData(queryKey, snapshot)
          toast.error(error.message || "Failed to move candidate")
        },
      }
    )
  }

  const showRestore =
    selectedIds.size > 0 &&
    candidates
      .filter((c) => selectedIds.has(c.resume_file_id))
      .every((c) => TERMINAL_STAGES.has(c.pipeline_stage))

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
          onExportCsv={() => {}}
          exportDisabled
        />
        <div className="flex items-center gap-2">
          {hasAnyRole("ORG_ADMIN", "SUPER_ADMIN") && <RecruiterWorkloadPanel />}
          <Button variant="outline" size="sm" asChild>
            <Link href="/candidates">
              <List className="size-3.5" aria-hidden="true" />
              Table
            </Link>
          </Button>
          <Button variant="default" size="sm" disabled>
            <LayoutGrid className="size-3.5" aria-hidden="true" />
            Board
          </Button>
        </div>
      </div>

      {selectedIds.size > 0 && (
        <CandidatesBulkActionBar
          selectedIds={Array.from(selectedIds)}
          onClear={() => setSelectedIds(new Set())}
          showRestore={showRestore}
        />
      )}

      {campaignsQuery.isSuccess && campaigns.length === 0 ? (
        <div className="rounded-lg border border-border px-4 py-8 text-center text-sm text-muted-foreground">
          No campaigns yet. Create a campaign and upload resumes to start reviewing candidates.
        </div>
      ) : candidatesQuery.isError ? (
        <DashboardErrorState error={candidatesQuery.error} onRetry={() => candidatesQuery.refetch()} />
      ) : (
        <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
          <div className="flex gap-3 overflow-x-auto pb-2">
            {PIPELINE_BOARD_COLUMNS.map((column) => (
              <PipelineBoardColumnView
                key={column.key}
                column={column}
                candidates={columns.get(column.key) ?? []}
                onEditNotes={setNotesCandidate}
                selectedIds={selectedIds}
                onToggleSelect={toggleSelect}
              />
            ))}
          </div>

          <div className="rounded-lg border border-border">
            <button
              type="button"
              className="flex w-full items-center justify-between px-4 py-2 text-sm font-medium text-foreground"
              onClick={() => setTerminalExpanded((v) => !v)}
            >
              <span>Terminal stages ({terminalCount})</span>
              <span className="text-muted-foreground">{terminalExpanded ? "Hide" : "Show"}</span>
            </button>
            {terminalExpanded && (
              <div className="flex gap-3 overflow-x-auto p-3 pt-0">
                {TERMINAL_BOARD_COLUMNS.map((column) => (
                  <PipelineBoardColumnView
                    key={column.key}
                    column={column}
                    candidates={columns.get(column.key) ?? []}
                    onEditNotes={setNotesCandidate}
                    selectedIds={selectedIds}
                    onToggleSelect={toggleSelect}
                  />
                ))}
              </div>
            )}
          </div>
        </DndContext>
      )}

      <CandidateNotesDialog
        candidate={notesCandidate}
        onOpenChange={(open) => {
          if (!open) setNotesCandidate(null)
        }}
      />
    </Stack>
  )
}

export { PipelineBoardView }
