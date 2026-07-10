"use client"

import { Building2, Clock, MapPin } from "lucide-react"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Card, CardContent } from "@/components/ui/card"
import { PipelineStageBadge, RecommendationBadge } from "@/features/candidates/candidate-badges"
import { CandidateActionsMenu } from "@/features/candidates/candidate-actions-menu"
import { initialsFromName } from "@/utils"
import type { CandidateListItem, CandidateProfile } from "@/types"

export interface CandidateProfileHeaderProps {
  profile: CandidateProfile
  actionsCandidate: CandidateListItem
  onEditNotes: () => void
}

function MetaItem({ icon: Icon, label }: { icon: typeof MapPin; label: string }) {
  return (
    <span className="flex items-center gap-1.5 text-caption text-muted-foreground">
      <Icon className="size-3.5 shrink-0" aria-hidden="true" />
      {label}
    </span>
  )
}

function CandidateProfileHeader({ profile, actionsCandidate, onEditNotes }: CandidateProfileHeaderProps) {
  return (
    <Card>
      <CardContent className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <Avatar size="lg" className="size-14">
            <AvatarFallback className="text-base">{initialsFromName(profile.candidate_name)}</AvatarFallback>
          </Avatar>
          <div className="flex flex-col gap-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-h4 text-foreground">{profile.candidate_name}</h2>
              <PipelineStageBadge stage={profile.pipeline_stage} />
              {profile.recommendation && <RecommendationBadge recommendation={profile.recommendation} />}
            </div>
            <p className="text-sm text-muted-foreground">
              {profile.current_role ?? "Role unknown"}
              {profile.current_company && ` at ${profile.current_company}`}
            </p>
            <div className="flex flex-wrap gap-x-4 gap-y-1">
              <MetaItem icon={MapPin} label={profile.location ?? "—"} />
              <MetaItem
                icon={Clock}
                label={
                  profile.years_of_experience !== null
                    ? `${profile.years_of_experience} yrs experience`
                    : "Experience unknown"
                }
              />
              <MetaItem icon={Building2} label={profile.campaign.title} />
            </div>
          </div>
        </div>

        <div className="flex flex-col items-end gap-3">
          {profile.overall_score !== null ? (
            <div className="flex flex-col items-end">
              <span className="text-caption text-muted-foreground">Overall AI Match</span>
              <span className="text-h3 font-semibold tabular-nums text-foreground">
                {profile.overall_score}%
              </span>
            </div>
          ) : (
            <span className="text-caption text-muted-foreground">
              {profile.ranking_available ? "Not yet ranked" : "Job description not ready"}
            </span>
          )}
          <CandidateActionsMenu
            candidate={actionsCandidate}
            onEditNotes={onEditNotes}
            campaignId={profile.campaign.id}
          />
        </div>
      </CardContent>
    </Card>
  )
}

export { CandidateProfileHeader }
