"use client"

import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import type { CandidateRanking, RankingRecommendation } from "@/types"

export interface CandidateDetailDialogProps {
  candidate: CandidateRanking | null
  onOpenChange: (open: boolean) => void
}

const RECOMMENDATION_VARIANT: Record<RankingRecommendation, React.ComponentProps<typeof Badge>["variant"]> = {
  "Strong Match": "active",
  "Good Match": "success",
  "Possible Match": "pending",
  "Not a Match": "destructive",
}

const SUB_SCORE_LABELS: [key: keyof CandidateRanking["sub_scores"], label: string][] = [
  ["semantic_score", "Semantic Fit"],
  ["skills_score", "Skills"],
  ["experience_score", "Experience"],
  ["education_score", "Education"],
  ["projects_score", "Projects"],
  ["certification_score", "Certifications"],
]

function CandidateDetailDialog({ candidate, onOpenChange }: CandidateDetailDialogProps) {
  return (
    <Dialog open={candidate !== null} onOpenChange={(open) => !open && onOpenChange(false)}>
      <DialogContent className="max-w-lg">
        {candidate && (
          <>
            <DialogHeader>
              <div className="flex items-center gap-2">
                <DialogTitle>{candidate.candidate_name}</DialogTitle>
                <Badge variant={RECOMMENDATION_VARIANT[candidate.recommendation]}>
                  {candidate.recommendation}
                </Badge>
              </div>
              {candidate.current_company && (
                <p className="text-caption text-muted-foreground">
                  {candidate.current_company}
                  {candidate.years_of_experience !== null && ` · ${candidate.years_of_experience} yrs experience`}
                </p>
              )}
            </DialogHeader>

            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between rounded-lg border border-border bg-muted/30 px-3 py-2">
                <span className="text-sm font-medium text-foreground">Overall Match Score</span>
                <span className="text-h4 font-semibold tabular-nums text-foreground">
                  {candidate.overall_score}%
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {SUB_SCORE_LABELS.map(([key, label]) => (
                  <div key={key} className="flex flex-col rounded-lg border border-border px-2.5 py-2">
                    <span className="text-caption text-muted-foreground">{label}</span>
                    <span className="text-sm font-semibold text-foreground">
                      {candidate.sub_scores[key]}
                    </span>
                  </div>
                ))}
              </div>

              <p className="text-sm text-foreground">{candidate.match_explanation}</p>

              {candidate.strengths.length > 0 && (
                <div className="flex flex-col gap-1">
                  <p className="text-caption font-medium text-success-emphasis">Strengths</p>
                  <ul className="list-inside list-disc text-sm text-foreground">
                    {candidate.strengths.map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}

              {candidate.weaknesses.length > 0 && (
                <div className="flex flex-col gap-1">
                  <p className="text-caption font-medium text-destructive-emphasis">Areas to probe</p>
                  <ul className="list-inside list-disc text-sm text-foreground">
                    {candidate.weaknesses.map((w) => (
                      <li key={w}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

export { CandidateDetailDialog }
