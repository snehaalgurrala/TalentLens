import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type {
  AssessmentSession,
  AssessmentSessionCampaignInfo,
  AssessmentSessionCandidateInfo,
  CommunicationAssessment,
} from "@/types"

import { formatDateTime, formatDuration, scoreTone } from "./format"

export interface AssessmentSummaryCardProps {
  session: AssessmentSession
  candidate: AssessmentSessionCandidateInfo
  campaign: AssessmentSessionCampaignInfo
  communicationAssessment: CommunicationAssessment | null
}

function AssessmentSummaryCard({
  session,
  candidate,
  campaign,
  communicationAssessment,
}: AssessmentSummaryCardProps) {
  const overallScore = communicationAssessment?.overall_score ?? null

  return (
    <Card>
      <CardHeader>
        <CardTitle>Assessment Summary</CardTitle>
        <p className="text-sm text-muted-foreground">
          {candidate.first_name} {candidate.last_name} &middot; {campaign.title}
        </p>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="flex flex-col gap-1">
          <span className="text-caption text-muted-foreground">Overall Status</span>
          <Badge variant={session.status === "COMPLETED" ? "success" : "pending"} className="w-fit">
            {session.status === "COMPLETED" ? "Completed" : "In Progress"}
          </Badge>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-caption text-muted-foreground">Assessment Date</span>
          <span className="text-sm font-medium text-foreground">{formatDateTime(session.started_at)}</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-caption text-muted-foreground">Assessment Duration</span>
          <span className="text-sm font-medium text-foreground">
            {formatDuration(session.started_at, session.completed_at)}
          </span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-caption text-muted-foreground">Overall Communication Score</span>
          {overallScore === null ? (
            <span className="text-sm text-muted-foreground">Pending</span>
          ) : (
            <span className={`text-h6 font-semibold tabular-nums ${scoreTone(overallScore)}`}>
              {overallScore}%
            </span>
          )}
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-caption text-muted-foreground">Overall Aptitude Score</span>
          <span className="text-sm text-muted-foreground">Aptitude scoring not yet available</span>
        </div>
      </CardContent>
    </Card>
  )
}

export { AssessmentSummaryCard }
