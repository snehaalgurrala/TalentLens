import { CheckCircle2, Circle } from "lucide-react"

import { cn } from "@/lib/utils"
import type { AssessmentSessionFull } from "@/types"

import { formatDateTime } from "./format"

export interface AssessmentTimelineProps {
  sessionFull: AssessmentSessionFull
}

interface TimelineStep {
  label: string
  timestamp: string | null
}

function latestCompletedTimestamp(
  timestamps: (string | null | undefined)[]
): string | null {
  const present = timestamps.filter((t): t is string => Boolean(t))
  if (present.length === 0) return null
  return present.reduce((latest, t) => (new Date(t) > new Date(latest) ? t : latest))
}

function buildSteps(sessionFull: AssessmentSessionFull): TimelineStep[] {
  const { session, recordings, communication_assessment: communicationAssessment } = sessionFull
  const readAloud = recordings.find((r) => r.recording.recording_type === "READ_ALOUD")
  const listenRepeat = recordings.find((r) => r.recording.recording_type === "LISTEN_REPEAT")

  const bothUploaded =
    readAloud?.recording.status === "UPLOADED" && listenRepeat?.recording.status === "UPLOADED"

  const transcriptsCompleted = recordings
    .map((r) => (r.transcript?.status === "COMPLETED" ? r.transcript.updated_at : null))
    .filter((t): t is string => Boolean(t))
  const allTranscribed = recordings.length > 0 && transcriptsCompleted.length === recordings.length

  const analysesCompleted = recordings
    .map((r) => (r.analysis?.status === "COMPLETED" ? r.analysis.updated_at : null))
    .filter((t): t is string => Boolean(t))
  const allAnalyzed = recordings.length > 0 && analysesCompleted.length === recordings.length

  return [
    { label: "Assessment Started", timestamp: session.started_at },
    {
      label: "Read Completed",
      timestamp: readAloud?.recording.status === "UPLOADED" ? readAloud.recording.uploaded_at : null,
    },
    {
      label: "Listen Completed",
      timestamp:
        listenRepeat?.recording.status === "UPLOADED" ? listenRepeat.recording.uploaded_at : null,
    },
    {
      label: "Upload Finished",
      timestamp: bothUploaded
        ? latestCompletedTimestamp([readAloud?.recording.uploaded_at, listenRepeat?.recording.uploaded_at])
        : null,
    },
    {
      label: "Transcription Completed",
      timestamp: allTranscribed ? latestCompletedTimestamp(transcriptsCompleted) : null,
    },
    {
      label: "Analysis Completed",
      timestamp: allAnalyzed ? latestCompletedTimestamp(analysesCompleted) : null,
    },
    {
      label: "Communication Assessment Generated",
      timestamp: communicationAssessment?.status === "COMPLETED" ? communicationAssessment.created_at : null,
    },
  ]
}

function AssessmentTimeline({ sessionFull }: AssessmentTimelineProps) {
  const steps = buildSteps(sessionFull)

  return (
    <ol className="flex flex-col gap-4" aria-label="Assessment processing timeline">
      {steps.map((step) => {
        const done = Boolean(step.timestamp)
        const Icon = done ? CheckCircle2 : Circle
        return (
          <li key={step.label} className="flex items-start gap-3">
            <span
              className={cn(
                "flex size-8 shrink-0 items-center justify-center rounded-full",
                done ? "bg-success/10 text-success-emphasis" : "bg-muted text-muted-foreground"
              )}
            >
              <Icon className="size-4" aria-hidden="true" />
            </span>
            <div className="flex flex-col gap-0.5">
              <p className="text-body text-foreground">{step.label}</p>
              <time className="text-caption text-muted-foreground">
                {step.timestamp ? formatDateTime(step.timestamp) : "Pending"}
              </time>
            </div>
          </li>
        )
      })}
    </ol>
  )
}

export { AssessmentTimeline }
