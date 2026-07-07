import { useMutation } from "@tanstack/react-query"

import { assessmentSessionService } from "@/services/assessment-session.service"
import type {
  ApiError,
  AssessmentRecording,
  AssessmentSession,
  AssessmentSessionCreate,
  RecordingType,
} from "@/types"

export function useCreateOrResumeSession() {
  return useMutation<AssessmentSession, ApiError, AssessmentSessionCreate>({
    mutationFn: (data) => assessmentSessionService.createOrResumeSession(data),
  })
}

interface UploadRecordingVariables {
  sessionId: string
  recordingType: RecordingType
  blob: Blob
  durationSeconds: number
  onUploadProgress?: (percent: number) => void
}

export function useUploadRecording() {
  return useMutation<AssessmentRecording, ApiError, UploadRecordingVariables>({
    mutationFn: ({ sessionId, recordingType, blob, durationSeconds, onUploadProgress }) =>
      assessmentSessionService.uploadRecording(
        sessionId,
        recordingType,
        blob,
        durationSeconds,
        onUploadProgress
      ),
  })
}
