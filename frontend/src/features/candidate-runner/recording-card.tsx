"use client"

import * as React from "react"
import { AlertTriangle, Loader2, Mic, Pause, Play, RotateCcw, Square, Trash2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { formatAudioDuration } from "@/utils/audio"
import { useAudioRecorder } from "./use-audio-recorder"
import type { RecordingAnswer } from "./types"

const MAX_DURATION_SECONDS = 60
const WAVEFORM_BAR_COUNT = 24

export interface RecordingCardProps {
  /** A recording restored from parent state (e.g. after navigating away and back). */
  value?: RecordingAnswer | null
  /** Called whenever the current recording changes — captured, re-recorded, or deleted — so the parent can persist it. */
  onChange?: (recording: RecordingAnswer | null) => void
  disabled?: boolean
  disabledReason?: string
  onContinue: (recording: RecordingAnswer) => void
  continueLabel?: string
  maxDurationSeconds?: number
}

/** Real microphone recording via the browser MediaRecorder API — capture, preview, re-record, delete. */
function RecordingCard({
  value = null,
  onChange,
  disabled = false,
  disabledReason,
  onContinue,
  continueLabel = "Continue",
  maxDurationSeconds = MAX_DURATION_SECONDS,
}: RecordingCardProps) {
  const { status, error, elapsedSeconds, recording, startRecording, stopRecording, reRecord, deleteRecording } =
    useAudioRecorder({ maxDurationSeconds, initialRecording: value })

  const [barHeights, setBarHeights] = React.useState<number[]>(() =>
    Array.from({ length: WAVEFORM_BAR_COUNT }, () => 20)
  )
  const audioRef = React.useRef<HTMLAudioElement | null>(null)
  const [isPlaying, setIsPlaying] = React.useState(false)
  const [previewElapsed, setPreviewElapsed] = React.useState(0)

  const onChangeRef = React.useRef(onChange)
  onChangeRef.current = onChange
  React.useEffect(() => {
    onChangeRef.current?.(recording)
  }, [recording])

  React.useEffect(() => {
    if (status !== "recording") return
    const interval = setInterval(() => {
      setBarHeights(Array.from({ length: WAVEFORM_BAR_COUNT }, () => 15 + Math.random() * 85))
    }, 150)
    return () => clearInterval(interval)
  }, [status])

  React.useEffect(() => {
    setIsPlaying(false)
    setPreviewElapsed(0)
  }, [recording?.url])

  const togglePlayback = () => {
    const audio = audioRef.current
    if (!audio || !recording) return
    if (isPlaying) {
      audio.pause()
      return
    }
    if (audio.ended || previewElapsed >= recording.durationSeconds) {
      audio.currentTime = 0
      setPreviewElapsed(0)
    }
    void audio.play()
  }

  const handleReRecord = () => {
    setIsPlaying(false)
    setPreviewElapsed(0)
    reRecord()
  }

  const handleDelete = () => {
    setIsPlaying(false)
    setPreviewElapsed(0)
    deleteRecording()
  }

  const handleContinue = () => {
    if (recording) onContinue(recording)
  }

  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-4 py-6">
        {status === "unsupported" && (
          <>
            <div className="flex size-16 items-center justify-center rounded-full bg-muted">
              <AlertTriangle className="size-7 text-muted-foreground" aria-hidden="true" />
            </div>
            <p className="text-center text-body text-muted-foreground">
              Your browser doesn&apos;t support audio recording. Please switch to a recent version
              of Chrome, Edge, or Brave to continue.
            </p>
          </>
        )}

        {status === "error" && (
          <>
            <div className="flex size-16 items-center justify-center rounded-full bg-destructive/10">
              <AlertTriangle className="size-7 text-destructive" aria-hidden="true" />
            </div>
            <p className="text-center text-body text-muted-foreground">
              {error?.message ?? "Something went wrong while accessing your microphone."}
            </p>
            <Button onClick={() => void startRecording()} variant="outline" size="lg">
              <Mic /> Try Again
            </Button>
          </>
        )}

        {status === "idle" && (
          <>
            <div className="flex size-16 items-center justify-center rounded-full bg-muted">
              <Mic className="size-7 text-muted-foreground" aria-hidden="true" />
            </div>
            <Button onClick={() => void startRecording()} disabled={disabled} size="lg">
              <Mic /> Start Recording
            </Button>
            {disabled && disabledReason && (
              <p className="text-caption text-muted-foreground">{disabledReason}</p>
            )}
          </>
        )}

        {status === "requesting-permission" && (
          <>
            <div className="flex size-16 items-center justify-center rounded-full bg-muted">
              <Loader2 className="size-7 animate-spin text-muted-foreground" aria-hidden="true" />
            </div>
            <p className="text-body text-muted-foreground">Requesting microphone access…</p>
          </>
        )}

        {status === "recording" && (
          <>
            <div
              className="flex items-center gap-2 text-body font-medium text-destructive-emphasis"
              role="status"
              aria-live="polite"
            >
              <span className="relative flex size-2.5">
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-destructive opacity-75" />
                <span className="relative inline-flex size-2.5 rounded-full bg-destructive" />
              </span>
              Recording… {formatAudioDuration(elapsedSeconds)}
            </div>
            <div className="flex h-16 w-full items-center justify-center gap-1" aria-hidden="true">
              {barHeights.map((height, index) => (
                <span
                  key={index}
                  className="w-1 rounded-full bg-primary transition-all duration-150"
                  style={{ height: `${height}%` }}
                />
              ))}
            </div>
            <Button onClick={stopRecording} variant="danger" size="lg">
              <Square /> Stop Recording
            </Button>
          </>
        )}

        {status === "recorded" && recording && (
          <>
            <audio
              ref={audioRef}
              src={recording.url}
              className="hidden"
              onTimeUpdate={(event) => setPreviewElapsed(event.currentTarget.currentTime)}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
              onEnded={() => {
                setIsPlaying(false)
                setPreviewElapsed(0)
              }}
            />
            <p className="text-caption text-muted-foreground">Preview your recording</p>
            <div className="flex w-full items-center gap-3">
              <Button
                onClick={togglePlayback}
                variant="outline"
                size="icon-lg"
                aria-label={isPlaying ? "Pause" : "Play"}
              >
                {isPlaying ? <Pause /> : <Play />}
              </Button>
              <div className="flex flex-1 flex-col gap-1">
                <Progress
                  value={
                    recording.durationSeconds > 0
                      ? (previewElapsed / recording.durationSeconds) * 100
                      : 0
                  }
                />
                <span className="text-caption text-muted-foreground tabular-nums">
                  {formatAudioDuration(previewElapsed)} / {formatAudioDuration(recording.durationSeconds)}
                </span>
              </div>
            </div>
            <div className="flex w-full flex-wrap items-center justify-center gap-3">
              <Button onClick={handleReRecord} variant="outline">
                <RotateCcw /> Re-record
              </Button>
              <Button onClick={handleDelete} variant="ghost">
                <Trash2 /> Delete
              </Button>
              <Button onClick={handleContinue}>{continueLabel}</Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

export { RecordingCard, MAX_DURATION_SECONDS }
