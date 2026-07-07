export type AssessmentSessionStatus = "IN_PROGRESS" | "COMPLETED"

export type AssessmentSection = "APTITUDE" | "READ_ALOUD" | "LISTEN_REPEAT"

export type RecordingType = "READ_ALOUD" | "LISTEN_REPEAT"

// Backend's persisted recording status — distinct from the client-local
// RecordingUploadStatus used to drive the uploading screen's progress UI.
export type RecordingStatus = "PENDING" | "UPLOADED" | "FAILED"

export interface AssessmentSession {
  id: string
  org_id: string
  campaign_id: string
  candidate_id: string
  current_section: AssessmentSection
  current_question: number | null
  status: AssessmentSessionStatus
  started_at: string
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface AssessmentSessionCreate {
  campaign_id: string
  candidate_id: string
}

export interface AssessmentRecording {
  id: string
  session_id: string
  recording_type: RecordingType
  filename: string
  mime_type: string
  duration_seconds: number
  storage_path: string
  file_size: number
  status: RecordingStatus
  uploaded_at: string | null
  created_at: string
  updated_at: string
}
