export interface AptitudeOption {
  id: string
  label: string
}

export interface AptitudeQuestion {
  id: number
  prompt: string
  options: AptitudeOption[]
}

export interface AssessmentMeta {
  title: string
  companyName: string
  estimatedMinutes: number
}

export type DeviceCheckKey = "browser" | "internet" | "speaker" | "microphone"

export interface DeviceCheckState {
  browser: boolean
  internet: boolean
  speaker: boolean
  microphone: boolean
}

export type RecordingStatus =
  | "idle"
  | "requesting-permission"
  | "recording"
  | "recorded"
  | "unsupported"
  | "error"

export type RecordingErrorReason =
  | "permission-denied"
  | "no-microphone"
  | "device-disconnected"
  | "unsupported-browser"
  | "unknown"

export interface RecordingError {
  reason: RecordingErrorReason
  message: string
}

/** A completed client-side recording, kept in memory (Blob + object URL) for playback and later upload. */
export interface RecordingAnswer {
  blob: Blob
  url: string
  durationSeconds: number
  mimeType: string
}

/** Client-local upload progress state — distinct from the backend's own
 * RecordingStatus (PENDING/UPLOADED/FAILED, from `@/types`), and from this
 * file's own recorder-state RecordingStatus above. */
export type RecordingUploadStatus = "idle" | "uploading" | "uploaded" | "failed"

export interface RecordingUploadState {
  status: RecordingUploadStatus
  progress: number
  error: string | null
}
