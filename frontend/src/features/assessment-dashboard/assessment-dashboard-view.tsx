"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Stack } from "@/components/layout/stack"
import { DashboardErrorState } from "@/features/dashboard"
import { useAssessmentSessionFull } from "@/hooks"

import { AssessmentSummaryCard } from "./assessment-summary-card"
import { AssessmentTimeline } from "./assessment-timeline"
import { AudioPlayerCard } from "./audio-player-card"
import { CommunicationOverviewCard } from "./communication-overview-card"
import { ProcessingStatusBadges } from "./processing-status-badges"
import { RecordingAnalysisCard } from "./recording-analysis-card"
import { StrengthsImprovements } from "./strengths-improvements"
import { WorkflowProgressStepper } from "./workflow-progress-stepper"

export interface AssessmentDashboardViewProps {
  sessionId: string
}

function AssessmentDashboardView({ sessionId }: AssessmentDashboardViewProps) {
  const query = useAssessmentSessionFull(sessionId)

  if (query.isPending) {
    return (
      <Stack gap="lg">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-64 w-full" />
      </Stack>
    )
  }

  if (query.isError) {
    return <DashboardErrorState error={query.error} onRetry={() => query.refetch()} />
  }

  const sessionFull = query.data
  const readAloud = sessionFull.recordings.find((r) => r.recording.recording_type === "READ_ALOUD")
  const listenRepeat = sessionFull.recordings.find(
    (r) => r.recording.recording_type === "LISTEN_REPEAT"
  )

  return (
    <Stack gap="lg">
      <AssessmentSummaryCard
        session={sessionFull.session}
        candidate={sessionFull.candidate}
        campaign={sessionFull.campaign}
        communicationAssessment={sessionFull.communication_assessment}
      />

      <WorkflowProgressStepper pipelineStage={sessionFull.pipeline_stage} />

      <Card>
        <CardHeader>
          <CardTitle>AI Processing Status</CardTitle>
        </CardHeader>
        <CardContent>
          <ProcessingStatusBadges sessionFull={sessionFull} />
        </CardContent>
      </Card>

      <CommunicationOverviewCard communicationAssessment={sessionFull.communication_assessment} />

      <StrengthsImprovements communicationAssessment={sessionFull.communication_assessment} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <RecordingAnalysisCard recordingType="READ_ALOUD" detail={readAloud} />
        <RecordingAnalysisCard recordingType="LISTEN_REPEAT" detail={listenRepeat} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <AudioPlayerCard sessionId={sessionId} recordingType="READ_ALOUD" detail={readAloud} />
        <AudioPlayerCard sessionId={sessionId} recordingType="LISTEN_REPEAT" detail={listenRepeat} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <AssessmentTimeline sessionFull={sessionFull} />
        </CardContent>
      </Card>
    </Stack>
  )
}

export { AssessmentDashboardView }
