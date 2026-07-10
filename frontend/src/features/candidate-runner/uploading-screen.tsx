"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { useMarkInvitationCompleted } from "@/hooks/use-assessment-invitations"
import { useUploadRecording } from "@/hooks/use-assessment-session"
import type { ApiError, RecordingType } from "@/types"
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
  updateUpload: (patch: Partial<RecordingUploadState>) => void,
  invitationToken: string | null
) {
  const mutation = useUploadRecording()
  const triggeredRef = React.useRef(false)

  React.useEffect(() => {
    if (!sessionId || !recording || upload.status !== "idle" || triggeredRef.current) return
    triggeredRef.current = true
    updateUpload({ status: "uploading", progress: 0, error: null })

    // mutateAsync (not mutate(vars, {onSuccess, onError})): the per-call
    // callback form only fires while the mutation observer still
    // "hasListeners()" (@tanstack/query-core mutationObserver.ts) — under
    // React 18 Strict Mode's dev-only mount→cleanup→remount cycle that can
    // momentarily be false right as the request settles, silently
    // dropping the callback and leaving the row stuck spinning forever
    // even though the upload actually succeeded server-side. mutateAsync's
    // promise resolves/rejects from Mutation.execute() directly, so it
    // isn't subject to that gating.
    mutation
      .mutateAsync({
        sessionId,
        recordingType,
        blob: recording.blob,
        durationSeconds: recording.durationSeconds,
        onUploadProgress: (percent) => updateUpload({ progress: percent }),
        invitationToken,
      })
      .then(() => updateUpload({ status: "uploaded", progress: 100, error: null }))
      .catch((error: ApiError) => updateUpload({ status: "failed", error: error.message }))
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
    invitationToken,
    readAloudRecording,
    readAloudUpload,
    updateReadAloudUpload,
    listenRepeatRecording,
    listenRepeatUpload,
    updateListenRepeatUpload,
  } = useAssessmentRunner()
  const markCompleted = useMarkInvitationCompleted()

  const readAloud = useRecordingUpload(
    sessionId,
    "READ_ALOUD",
    readAloudRecording,
    readAloudUpload,
    updateReadAloudUpload,
    invitationToken
  )
  const listenRepeat = useRecordingUpload(
    sessionId,
    "LISTEN_REPEAT",
    listenRepeatRecording,
    listenRepeatUpload,
    updateListenRepeatUpload,
    invitationToken
  )

  const bothUploaded = readAloudUpload.status === "uploaded" && listenRepeatUpload.status === "uploaded"
  const completionReportedRef = React.useRef(false)

  React.useEffect(() => {
    if (!bothUploaded) return
    // Best-effort: this is a lifecycle side-signal for the recruiter
    // dashboard, not a gate on the candidate's own progress, so a failure
    // here must never block navigation to the completed screen.
    if (invitationToken && !completionReportedRef.current) {
      completionReportedRef.current = true
      markCompleted.mutate(invitationToken)
    }
    const timeout = setTimeout(() => router.push("/assessment/completed"), 600)
    return () => clearTimeout(timeout)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bothUploaded, router, invitationToken])

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
