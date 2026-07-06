"use client"

import * as React from "react"
import { useDraggable } from "@dnd-kit/core"
import { useRouter } from "next/navigation"
import { Building2, UserRound } from "lucide-react"

import { CandidateCard } from "@/components/ui/candidate-card"
import { CandidateActionsMenu } from "@/features/candidates"
import { PIPELINE_STAGE_LABELS, PIPELINE_STAGE_VARIANT } from "@/features/candidates/constants"
import { initialsFromName } from "@/utils"
import type { CandidateListItem } from "@/types"

export interface PipelineBoardCardProps {
  candidate: CandidateListItem
  onEditNotes: (candidate: CandidateListItem) => void
}

function PipelineBoardCard({ candidate, onEditNotes }: PipelineBoardCardProps) {
  const router = useRouter()
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: candidate.resume_file_id,
    data: { candidate },
  })

  const style: React.CSSProperties = transform
    ? {
        transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
        zIndex: isDragging ? 10 : undefined,
        opacity: isDragging ? 0.5 : undefined,
      }
    : {}

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners} className="touch-none">
      <CandidateCard
        name={candidate.candidate_name}
        initials={initialsFromName(candidate.candidate_name)}
        status={{
          label: PIPELINE_STAGE_LABELS[candidate.pipeline_stage],
          variant: PIPELINE_STAGE_VARIANT[candidate.pipeline_stage],
        }}
        matchScore={candidate.overall_score ?? undefined}
        meta={[
          ...(candidate.current_company ? [{ icon: Building2, label: candidate.current_company }] : []),
          { icon: UserRound, label: candidate.assigned_recruiter?.full_name ?? "Unassigned" },
        ]}
        onClick={() => router.push(`/candidates/${candidate.candidate_id}`)}
        className="cursor-pointer"
        actions={
          <div onPointerDown={(e) => e.stopPropagation()} onClick={(e) => e.stopPropagation()}>
            <CandidateActionsMenu candidate={candidate} onEditNotes={onEditNotes} />
          </div>
        }
      />
    </div>
  )
}

export { PipelineBoardCard }
