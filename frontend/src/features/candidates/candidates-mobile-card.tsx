"use client"

import { Briefcase, Calendar, GraduationCap } from "lucide-react"

import { CandidateCard } from "@/components/ui/candidate-card"
import { Checkbox } from "@/components/ui/checkbox"
import { formatDate, initialsFromName } from "@/utils"
import type { CandidateListItem } from "@/types"

import { CandidateActionsMenu } from "./candidate-actions-menu"
import { PIPELINE_STAGE_VARIANT, PIPELINE_STAGE_LABELS } from "./constants"

export interface CandidatesMobileCardsProps {
  candidates: CandidateListItem[]
  selectedIds: Set<string>
  onToggleSelect: (id: string) => void
  onEditNotes: (candidate: CandidateListItem) => void
}

function CandidatesMobileCards({ candidates, selectedIds, onToggleSelect, onEditNotes }: CandidatesMobileCardsProps) {
  return (
    <div className="flex flex-col gap-3 md:hidden">
      {candidates.map((candidate) => (
        <CandidateCard
          key={candidate.resume_file_id}
          name={candidate.candidate_name}
          role={candidate.current_role ?? undefined}
          initials={initialsFromName(candidate.candidate_name)}
          matchScore={candidate.overall_score ?? undefined}
          status={{
            label: PIPELINE_STAGE_LABELS[candidate.pipeline_stage],
            variant: PIPELINE_STAGE_VARIANT[candidate.pipeline_stage],
          }}
          meta={[
            ...(candidate.current_company
              ? [{ icon: Briefcase, label: candidate.current_company }]
              : []),
            ...(candidate.education[0]?.institution
              ? [{ icon: GraduationCap, label: candidate.education[0].institution as string }]
              : []),
            { icon: Calendar, label: `Uploaded ${formatDate(candidate.applied_at)}` },
          ]}
          actions={
            <div className="flex items-center gap-2">
              <Checkbox
                checked={selectedIds.has(candidate.resume_file_id)}
                onCheckedChange={() => onToggleSelect(candidate.resume_file_id)}
                aria-label={`Select ${candidate.candidate_name}`}
              />
              <CandidateActionsMenu candidate={candidate} onEditNotes={onEditNotes} />
            </div>
          }
        />
      ))}
    </div>
  )
}

export { CandidatesMobileCards }
