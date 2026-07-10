"use client"

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
  campaignId: string
}

function PipelineBoardCard({ candidate, onEditNotes, campaignId }: PipelineBoardCardProps) {
  const router = useRouter()

  return (
    <div>
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
            <CandidateActionsMenu candidate={candidate} onEditNotes={onEditNotes} campaignId={campaignId} />
          </div>
        }
      />
    </div>
  )
}

export { PipelineBoardCard }
