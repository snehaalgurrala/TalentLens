import { Badge } from "@/components/ui/badge"
import type { AssessmentSessionFull } from "@/types"

export interface ProcessingStatusBadgesProps {
  sessionFull: AssessmentSessionFull
}

function ProcessingStatusBadges({ sessionFull }: ProcessingStatusBadgesProps) {
  const { recordings, communication_assessment: communicationAssessment } = sessionFull

  const uploaded = recordings.length > 0 && recordings.every((r) => r.recording.status === "UPLOADED")
  const anyUploadFailed = recordings.some((r) => r.recording.status === "FAILED")

  const transcribed = recordings.length > 0 && recordings.every((r) => r.transcript?.status === "COMPLETED")
  const anyTranscriptFailed = recordings.some((r) => r.transcript?.status === "FAILED")

  const analyzed = recordings.length > 0 && recordings.every((r) => r.analysis?.status === "COMPLETED")
  const anyAnalysisFailed = recordings.some((r) => r.analysis?.status === "FAILED")

  const completed = communicationAssessment?.status === "COMPLETED"
  const communicationFailed = communicationAssessment?.status === "FAILED"

  function stageBadge(label: string, done: boolean, failed: boolean) {
    const variant = failed ? "destructive" : done ? "success" : "pending"
    const text = failed ? `${label} Failed` : done ? label : `${label} Pending`
    return (
      <Badge key={label} variant={variant}>
        {text}
      </Badge>
    )
  }

  return (
    <div className="flex flex-wrap gap-2" role="list" aria-label="AI processing status">
      {stageBadge("Uploaded", uploaded, anyUploadFailed)}
      {stageBadge("Transcribed", transcribed, anyTranscriptFailed)}
      {stageBadge("Analyzed", analyzed, anyAnalysisFailed)}
      {stageBadge("Completed", completed, communicationFailed)}
    </div>
  )
}

export { ProcessingStatusBadges }
