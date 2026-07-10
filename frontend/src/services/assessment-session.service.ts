import { api } from "@/services/api"
import type {
  AssessmentRecording,
  AssessmentSession,
  AssessmentSessionCreate,
  RecordingType,
} from "@/types"

function extensionForMimeType(mimeType: string): string {
  const base = mimeType.split(";")[0]?.trim().toLowerCase()
  if (base === "audio/ogg") return "ogg"
  return "webm"
}

export const assessmentSessionService = {
  createOrResumeSession: (data: AssessmentSessionCreate) =>
    api.post<AssessmentSession>("/assessment/session", data),

  uploadRecording: (
    sessionId: string,
    recordingType: RecordingType,
    blob: Blob,
    durationSeconds: number,
    onUploadProgress?: (percent: number) => void,
    /** Candidates have no platform account/JWT, so the token-flow entry
     * point (invitation-entry-screen.tsx) passes this through instead —
     * the backend accepts either a recruiter JWT or this header, scoped
     * to the exact session the invitation was issued for. */
    invitationToken?: string | null
  ) => {
    const filename = `${recordingType.toLowerCase()}.${extensionForMimeType(blob.type)}`
    const formData = new FormData()
    formData.append("file", blob, filename)
    formData.append("duration_seconds", String(durationSeconds))
    return api.post<AssessmentRecording>(
      `/assessment/session/${sessionId}/recordings/${recordingType}/upload`,
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
          ...(invitationToken ? { "X-Assessment-Token": invitationToken } : {}),
        },
        onUploadProgress: onUploadProgress
          ? (event) => {
              if (event.total) onUploadProgress(Math.round((event.loaded / event.total) * 100))
            }
          : undefined,
      }
    )
  },
}
