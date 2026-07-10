"use client"

import * as React from "react"

import { getSupportedAudioMimeType, isAudioRecordingSupported } from "@/utils/audio"
import type { RecordingAnswer, RecordingError, RecordingErrorReason, RecordingStatus } from "./types"

const DEFAULT_MAX_DURATION_SECONDS = 60

// Bare (non-`exact`) values are "ideal" hints per the MediaTrackConstraints
// spec — unsupported constraints or devices that can't hit the ideal value
// are ignored rather than rejected, so this never throws OverconstrainedError.
// Matches what Whisper resamples to anyway (mono/16kHz), and the AEC/NS/AGC
// trio reduces the noise Whisper otherwise has to transcribe through.
const AUDIO_CONSTRAINTS: MediaTrackConstraints = {
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
  channelCount: 1,
  sampleRate: 16000,
}

export interface UseAudioRecorderOptions {
  maxDurationSeconds?: number
  /** A previously captured recording (e.g. restored from context after navigating back). */
  initialRecording?: RecordingAnswer | null
}

export interface UseAudioRecorderResult {
  status: RecordingStatus
  error: RecordingError | null
  elapsedSeconds: number
  recording: RecordingAnswer | null
  startRecording: () => Promise<void>
  stopRecording: () => void
  reRecord: () => void
  deleteRecording: () => void
}

function getMicrophoneError(err: unknown): RecordingError {
  const name = err instanceof DOMException ? err.name : undefined
  let reason: RecordingErrorReason = "unknown"
  let message = "We couldn't access your microphone. Please check your device and try again."

  if (name === "NotAllowedError" || name === "PermissionDeniedError" || name === "SecurityError") {
    reason = "permission-denied"
    message =
      "Microphone access was denied. Please allow microphone access in your browser settings and try again."
  } else if (name === "NotFoundError" || name === "DevicesNotFoundError") {
    reason = "no-microphone"
    message = "No microphone was found. Please connect a microphone and try again."
  } else if (name === "NotReadableError" || name === "TrackStartError") {
    reason = "device-disconnected"
    message = "Your microphone couldn't be started. It may be in use by another application."
  }

  return { reason, message }
}

function useAudioRecorder(options: UseAudioRecorderOptions = {}): UseAudioRecorderResult {
  const { maxDurationSeconds = DEFAULT_MAX_DURATION_SECONDS, initialRecording = null } = options

  const [status, setStatus] = React.useState<RecordingStatus>(initialRecording ? "recorded" : "idle")
  const [error, setError] = React.useState<RecordingError | null>(null)
  const [elapsedSeconds, setElapsedSeconds] = React.useState(initialRecording?.durationSeconds ?? 0)
  const [recording, setRecording] = React.useState<RecordingAnswer | null>(initialRecording)

  const mediaRecorderRef = React.useRef<MediaRecorder | null>(null)
  const streamRef = React.useRef<MediaStream | null>(null)
  const chunksRef = React.useRef<Blob[]>([])
  const startedAtRef = React.useRef(0)
  const intervalRef = React.useRef<ReturnType<typeof setInterval> | null>(null)

  // Feature detection must happen after mount so server/client first render match.
  React.useEffect(() => {
    if (!isAudioRecordingSupported()) {
      setStatus((prev) => (prev === "recorded" ? prev : "unsupported"))
    }
  }, [])

  const clearTimer = React.useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  const releaseStream = React.useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }, [])

  React.useEffect(() => {
    return () => {
      clearTimer()
      releaseStream()
    }
  }, [clearTimer, releaseStream])

  const stopRecording = React.useCallback(() => {
    clearTimer()
    const recorder = mediaRecorderRef.current
    if (recorder && recorder.state !== "inactive") {
      recorder.stop()
    }
    releaseStream()
  }, [clearTimer, releaseStream])

  const startRecording = React.useCallback(async () => {
    if (!isAudioRecordingSupported()) {
      setError({
        reason: "unsupported-browser",
        message: "Your browser doesn't support audio recording. Please use Chrome, Edge, or Brave.",
      })
      setStatus("unsupported")
      return
    }

    setError(null)
    setStatus("requesting-permission")

    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: AUDIO_CONSTRAINTS })
    } catch (err) {
      setError(getMicrophoneError(err))
      setStatus("error")
      return
    }

    streamRef.current = stream

    const mimeType = getSupportedAudioMimeType()
    const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)
    mediaRecorderRef.current = recorder
    chunksRef.current = []

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data)
    }

    recorder.onstop = () => {
      const durationSeconds = Math.min(
        maxDurationSeconds,
        Math.round((Date.now() - startedAtRef.current) / 1000)
      )
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" })
      chunksRef.current = []
      const url = URL.createObjectURL(blob)
      setRecording({ blob, url, durationSeconds, mimeType: recorder.mimeType || "audio/webm" })
      setStatus("recorded")
    }

    const [track] = stream.getAudioTracks()
    if (track) {
      track.onended = () => {
        clearTimer()
        setError({
          reason: "device-disconnected",
          message: "Your microphone was disconnected. Please reconnect it and try again.",
        })
        setStatus("error")
      }
    }

    startedAtRef.current = Date.now()
    setElapsedSeconds(0)
    recorder.start()
    setStatus("recording")

    intervalRef.current = setInterval(() => {
      setElapsedSeconds((prev) => {
        const next = prev + 1
        if (next >= maxDurationSeconds) {
          stopRecording()
          return maxDurationSeconds
        }
        return next
      })
    }, 1000)
  }, [maxDurationSeconds, stopRecording, clearTimer])

  const clearRecording = React.useCallback(() => {
    setRecording((prev) => {
      if (prev) URL.revokeObjectURL(prev.url)
      return null
    })
    setElapsedSeconds(0)
    setError(null)
    setStatus(isAudioRecordingSupported() ? "idle" : "unsupported")
  }, [])

  return {
    status,
    error,
    elapsedSeconds,
    recording,
    startRecording,
    stopRecording,
    reRecord: clearRecording,
    deleteRecording: clearRecording,
  }
}

export { useAudioRecorder }
