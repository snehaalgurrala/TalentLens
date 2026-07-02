"use client"

import { Briefcase, Building2 } from "lucide-react"

import { CandidateCard } from "@/components/ui/candidate-card"
import type { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { Stack } from "@/components/layout/stack"
import type { CandidateReviewStatus, TopCandidate } from "@/types"

export interface TopCandidatesListProps {
  candidates: TopCandidate[]
  isLoading: boolean
}

const REVIEW_STATUS_BADGE: Record<
  CandidateReviewStatus,
  { label: string; variant: React.ComponentProps<typeof Badge>["variant"] }
> = {
  PENDING: { label: "Pending Review", variant: "pending" },
  SHORTLISTED: { label: "Shortlisted", variant: "shortlisted" },
  REJECTED: { label: "Rejected", variant: "rejected" },
}

function initials(name: string): string {
  const parts = name.split(" ").filter(Boolean)
  const letters = parts.slice(0, 2).map((part) => part[0]?.toUpperCase() ?? "")
  return letters.join("") || "?"
}

function TopCandidatesList({ candidates, isLoading }: TopCandidatesListProps) {
  if (isLoading) {
    return (
      <Stack gap="sm">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-24 w-full rounded-xl" />
        ))}
      </Stack>
    )
  }

  if (candidates.length === 0) {
    return (
      <TableEmptyState
        icon={Building2}
        title="No ranked candidates yet"
        description="Candidates appear here once a campaign has a parsed job description and ranked resumes."
      />
    )
  }

  return (
    <Stack gap="sm" role="list" aria-label="Top ranked candidates">
      {candidates.map((candidate, index) => {
        const status = REVIEW_STATUS_BADGE[candidate.review_status]
        const meta = [
          ...(candidate.current_company
            ? [{ icon: Building2, label: candidate.current_company }]
            : []),
          ...(candidate.years_of_experience != null
            ? [{ icon: Briefcase, label: `${candidate.years_of_experience} yrs experience` }]
            : []),
        ]

        return (
          <div key={candidate.resume_file_id} role="listitem" className="relative">
            <span
              className="absolute -top-2 -left-2 z-10 flex size-6 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground ring-2 ring-background"
              aria-label={`Rank ${index + 1}`}
            >
              {index + 1}
            </span>
            <CandidateCard
              name={candidate.candidate_name}
              role={candidate.campaign_name}
              initials={initials(candidate.candidate_name)}
              matchScore={Math.round(candidate.match_score)}
              status={{ label: status.label, variant: status.variant }}
              meta={meta}
            />
          </div>
        )
      })}
    </Stack>
  )
}

export { TopCandidatesList }
