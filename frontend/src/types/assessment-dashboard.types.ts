import type { AssessmentRecording, AssessmentSession, RecordingType } from "./assessment-session.types"

export type TranscriptStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED"

export interface AssessmentTranscript {
  id: string
  recording_id: string
  status: TranscriptStatus
  transcript: string | null
  language: string | null
  model_name: string | null
  processing_time_ms: number | null
  segment_count: number | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export type AnalysisType = RecordingType

export type AnalysisStatus = "PENDING" | "COMPLETED" | "FAILED"

export interface AssessmentAnalysis {
  id: string
  transcript_id: string
  analysis_type: AnalysisType
  status: AnalysisStatus
  overall_score: number | null
  word_accuracy: number | null
  correct_words: number | null
  missing_words: number | null
  extra_words: number | null
  substituted_words: number | null
  total_words: number | null
  reading_speed_wpm: number | null
  completion_percentage: number | null
  semantic_similarity: number | null
  keyword_coverage: number | null
  analysis_json: Record<string, unknown> | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export type CommunicationAssessmentStatus = "PENDING" | "COMPLETED" | "FAILED"

export interface CommunicationAssessment {
  id: string
  assessment_session_id: string
  status: CommunicationAssessmentStatus
  overall_score: number | null
  reading_score: number | null
  listening_score: number | null
  confidence_score: number | null
  strengths_json: string[] | null
  improvements_json: string[] | null
  summary_json: Record<string, unknown> | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface AssessmentRecordingDetail {
  recording: AssessmentRecording
  reference_sentence: string
  transcript: AssessmentTranscript | null
  analysis: AssessmentAnalysis | null
}

export interface AssessmentSessionFull {
  session: AssessmentSession
  recordings: AssessmentRecordingDetail[]
  communication_assessment: CommunicationAssessment | null
}
