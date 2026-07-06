"use client"

import { useDroppable } from "@dnd-kit/core"

import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { cn } from "@/lib/utils"
import type { CandidateListItem } from "@/types"

import type { PipelineBoardColumn } from "./constants"
import { PipelineBoardCard } from "./pipeline-board-card"

export interface PipelineBoardColumnViewProps {
  column: PipelineBoardColumn
  candidates: CandidateListItem[]
  onEditNotes: (candidate: CandidateListItem) => void
  selectedIds: Set<string>
  onToggleSelect: (id: string) => void
}

function PipelineBoardColumnView({
  column,
  candidates,
  onEditNotes,
  selectedIds,
  onToggleSelect,
}: PipelineBoardColumnViewProps) {
  const { setNodeRef, isOver } = useDroppable({ id: column.key, data: { column } })

  return (
    <div
      ref={setNodeRef}
      className={cn(
        "flex w-72 shrink-0 flex-col gap-2 rounded-lg border border-border bg-muted/30 p-2 transition-colors",
        isOver && "border-primary bg-primary/5"
      )}
    >
      <div className="flex items-center justify-between gap-2 px-1 py-1">
        <span className="text-sm font-medium text-foreground">{column.label}</span>
        <Badge variant="secondary">{candidates.length}</Badge>
      </div>
      <div className="flex flex-col gap-2 overflow-y-auto" style={{ maxHeight: "calc(100vh - 22rem)" }}>
        {candidates.length === 0 ? (
          <div className="rounded-md border border-dashed border-border px-3 py-6 text-center text-caption text-muted-foreground">
            No candidates
          </div>
        ) : (
          candidates.map((candidate) => (
            <div key={candidate.resume_file_id} className="relative">
              <Checkbox
                checked={selectedIds.has(candidate.resume_file_id)}
                onCheckedChange={() => onToggleSelect(candidate.resume_file_id)}
                onClick={(e) => e.stopPropagation()}
                aria-label={`Select ${candidate.candidate_name}`}
                className="absolute top-3 left-3 z-10 bg-background"
              />
              <PipelineBoardCard candidate={candidate} onEditNotes={onEditNotes} />
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export { PipelineBoardColumnView }
