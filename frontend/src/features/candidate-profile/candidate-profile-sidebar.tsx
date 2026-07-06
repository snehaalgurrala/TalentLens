"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { PipelineStageBadge, RecommendationBadge } from "@/features/candidates/candidate-badges"
import { formatDateTime } from "@/utils"
import type { CandidateProfile } from "@/types"

export interface CandidateProfileSidebarProps {
  profile: CandidateProfile
}

function SidebarField({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-caption text-muted-foreground">{label}</span>
      <span className="text-sm font-medium text-foreground">{value}</span>
    </div>
  )
}

function CandidateProfileSidebar({ profile }: CandidateProfileSidebarProps) {
  return (
    <Card className="sticky top-4 h-fit">
      <CardHeader>
        <CardTitle>At a Glance</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <SidebarField
          label="Overall Score"
          value={profile.overall_score !== null ? `${profile.overall_score}%` : "—"}
        />
        <SidebarField label="Pipeline Stage" value={<PipelineStageBadge stage={profile.pipeline_stage} />} />
        <SidebarField
          label="Recruiter"
          value={profile.assigned_recruiter?.full_name ?? "Unassigned"}
        />
        <SidebarField label="Campaign" value={profile.campaign.title} />
        <SidebarField label="Resume Status" value={profile.upload_status} />
        <SidebarField
          label="AI Recommendation"
          value={<RecommendationBadge recommendation={profile.recommendation} />}
        />
        <SidebarField label="Last Updated" value={formatDateTime(profile.uploaded_at)} />
      </CardContent>
    </Card>
  )
}

export { CandidateProfileSidebar }
