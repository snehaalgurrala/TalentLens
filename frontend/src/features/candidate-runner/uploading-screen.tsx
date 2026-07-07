"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { useUploadRecording } from "@/hooks/use-assessment-session"
import type { RecordingType } from "@/types"
import { useAssessmentRunner } from "./assessment-runner-context"
import { AssessmentScreenShell } from "./assessment-screen-shell"
import type { RecordingAnswer, RecordingUploadState } from "./types"

interface UploadRowProps {
  label: string
  upload: RecordingUploadState
  onRetry: () => void
}

function UploadRow({ label, upload, onRetry }: UploadRowProps) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2.5 text-sm">
        {upload.status === "uploaded" ? (
          <CheckCircle2 className="size-4 shrink-0 text-success" aria-hidden="true" />
        ) : upload.status === "failed" ? (
          <AlertCircle className="size-4 shrink-0 text-destructive" aria-hidden="true" />
        ) : (
          <Loader2 className="size-4 shrink-0 animate-spin text-primary" aria-hidden="true" />
        )}
        <span className="text-foreground">{label}</span>
      </div>
      <Progress value={upload.status === "uploaded" ? 100 : upload.progress} />
      {upload.status === "failed" && (
        <div className="flex items-center justify-between gap-2">
          <span className="text-caption text-destructive">
            {upload.error ?? "Upload failed."}
          </span>
          <Button size="sm" variant="outline" onClick={onRetry}>
            Retry
          </Button>
        </div>
      )}
    </div>
  )
}

function useRecordingUpload(
  sessionId: string | null,
  recordingType: RecordingType,
  recording: RecordingAnswer | null,
  upload: RecordingUploadState,
  updateUpload: (patch: Partial<RecordingUploadState>) => void
) {
  const mutation = useUploadRecording()
  const triggeredRef = React.useRef(false)

  React.useEffect(() => {
    if (!sessionId || !recording || upload.status !== "idle" || triggeredRef.current) return
    triggeredRef.current = true
    updateUpload({ status: "uploading", progress: 0, error: null })
    mutation.mutate(
      {
        sessionId,
        recordingType,
        blob: recording.blob,
        durationSeconds: recording.durationSeconds,
        onUploadProgress: (percent) => updateUpload({ progress: percent }),
      },
      {
        onSuccess: () => updateUpload({ status: "uploaded", progress: 100, error: null }),
        onError: (error) => updateUpload({ status: "failed", error: error.message }),
      }
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, recording, upload.status])

  const retry = React.useCallback(() => {
    triggeredRef.current = false
    updateUpload({ status: "idle", progress: 0, error: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return { retry }
}

function UploadingScreen() {
  const router = useRouter()
  const {
    sessionId,
    readAloudRecording,
    readAloudUpload,
    updateReadAloudUpload,
    listenRepeatRecording,
    listenRepeatUpload,
    updateListenRepeatUpload,
  } = useAssessmentRunner()

  const readAloud = useRecordingUpload(
    sessionId,
    "READ_ALOUD",
    readAloudRecording,
    readAloudUpload,
    updateReadAloudUpload
  )
  const listenRepeat = useRecordingUpload(
    sessionId,
    "LISTEN_REPEAT",
    listenRepeatRecording,
    listenRepeatUpload,
    updateListenRepeatUpload
  )

  const bothUploaded = readAloudUpload.status === "uploaded" && listenRepeatUpload.status === "uploaded"

  React.useEffect(() => {
    if (!bothUploaded) return
    const timeout = setTimeout(() => router.push("/assessment/completed"), 600)
    return () => clearTimeout(timeout)
  }, [bothUploaded, router])

  if (!sessionId) {
    return (
      <AssessmentScreenShell>
        <Card>
          <CardHeader className="items-center text-center">
            <CardTitle>Session Not Found</CardTitle>
            <CardDescription>
              We couldn&apos;t find your assessment session. Please return to the start of the
              assessment link to try again.
            </CardDescription>
          </CardHeader>
        </Card>
      </AssessmentScreenShell>
    )
  }

  return (
    <AssessmentScreenShell>
      <Card>
        <CardHeader className="items-center text-center">
          <CardTitle>Submitting Your Assessment</CardTitle>
          <CardDescription>This will only take a moment. Please don&apos;t close this page.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          <UploadRow label="Read Aloud" upload={readAloudUpload} onRetry={readAloud.retry} />
          <UploadRow label="Listen & Repeat" upload={listenRepeatUpload} onRetry={listenRepeat.retry} />
        </CardContent>
      </Card>
    </AssessmentScreenShell>
  )
}

export { UploadingScreen }
