"use client"

import * as React from "react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { assessmentDashboardService } from "@/services/assessment-dashboard.service"
import type { AssessmentRecordingDetail, RecordingType } from "@/types"

export interface AudioPlayerCardProps {
  sessionId: string
  recordingType: RecordingType
  detail: AssessmentRecordingDetail | undefined
}

const TITLE_BY_TYPE: Record<RecordingType, string> = {
  READ_ALOUD: "Read Aloud Recording",
  LISTEN_REPEAT: "Listen & Repeat Recording",
}

function AudioPlayerCard({ sessionId, recordingType, detail }: AudioPlayerCardProps) {
  const [blobUrl, setBlobUrl] = React.useState<string | null>(null)
  const [isLoading, setIsLoading] = React.useState(true)
  const [error, setError] = React.useState(false)
  const isUploaded = detail?.recording.status === "UPLOADED"

  React.useEffect(() => {
    if (!isUploaded) {
      setIsLoading(false)
      return
    }

    let cancelled = false
    let objectUrl: string | null = null

    async function load() {
      setIsLoading(true)
      setError(false)
      try {
        const { blob } = await assessmentDashboardService.downloadRecording(sessionId, recordingType)
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setBlobUrl(objectUrl)
      } catch {
        if (!cancelled) setError(true)
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    void load()
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [sessionId, recordingType, isUploaded])

  return (
    <Card>
      <CardHeader>
        <CardTitle>{TITLE_BY_TYPE[recordingType]}</CardTitle>
      </CardHeader>
      <CardContent>
        {!isUploaded ? (
          <p className="text-sm text-muted-foreground">Recording unavailable.</p>
        ) : isLoading ? (
          <Skeleton className="h-12 w-full" />
        ) : error ? (
          <p className="text-sm text-muted-foreground">Couldn&rsquo;t load this recording.</p>
        ) : (
          <audio
            controls
            src={blobUrl ?? undefined}
            className="w-full"
            aria-label={TITLE_BY_TYPE[recordingType]}
          >
            Your browser doesn&rsquo;t support audio playback.
          </audio>
        )}
      </CardContent>
    </Card>
  )
}

export { AudioPlayerCard }
