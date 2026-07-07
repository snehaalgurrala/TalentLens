import { render, screen } from "@testing-library/react"

import type { AssessmentRecordingDetail } from "@/types"

import { RecordingAnalysisCard } from "./recording-analysis-card"

const now = new Date().toISOString()

function makeDetail(overrides: Partial<AssessmentRecordingDetail> = {}): AssessmentRecordingDetail {
  return {
    recording: {
      id: "rec-1",
      session_id: "session-1",
      recording_type: "READ_ALOUD",
      filename: "clip.webm",
      mime_type: "audio/webm",
      duration_seconds: 12.5,
      storage_path: "x/y.webm",
      file_size: 4096,
      status: "UPLOADED",
      uploaded_at: now,
      created_at: now,
      updated_at: now,
    },
    reference_sentence: "The quick brown fox jumps over the lazy dog.",
    transcript: null,
    analysis: null,
    ...overrides,
  }
}

describe("RecordingAnalysisCard", () => {
  it("renders a not-recorded empty state when no recording exists", () => {
    render(<RecordingAnalysisCard recordingType="READ_ALOUD" detail={undefined} />)

    expect(screen.getByText(/hasn.t recorded this section yet/i)).toBeInTheDocument()
  })

  it("shows a transcription-in-progress badge while the transcript is pending", () => {
    render(<RecordingAnalysisCard recordingType="READ_ALOUD" detail={makeDetail()} />)

    expect(screen.getByText("Transcription in progress")).toBeInTheDocument()
  })

  it("shows the transcription failure message", () => {
    render(
      <RecordingAnalysisCard
        recordingType="READ_ALOUD"
        detail={makeDetail({
          transcript: {
            id: "t1",
            recording_id: "rec-1",
            status: "FAILED",
            transcript: null,
            language: null,
            model_name: null,
            processing_time_ms: null,
            segment_count: null,
            error_message: "Whisper timed out",
            created_at: now,
            updated_at: now,
          },
        })}
      />
    )

    expect(screen.getByText("Whisper timed out")).toBeInTheDocument()
  })

  it("shows Read Aloud metrics once analysis completes", () => {
    render(
      <RecordingAnalysisCard
        recordingType="READ_ALOUD"
        detail={makeDetail({
          transcript: {
            id: "t1",
            recording_id: "rec-1",
            status: "COMPLETED",
            transcript: "The quick brown fox jumps over the lazy dog.",
            language: "en",
            model_name: "whisper-base",
            processing_time_ms: 800,
            segment_count: 1,
            error_message: null,
            created_at: now,
            updated_at: now,
          },
          analysis: {
            id: "a1",
            transcript_id: "t1",
            analysis_type: "READ_ALOUD",
            status: "COMPLETED",
            overall_score: 91,
            word_accuracy: 95,
            correct_words: 18,
            missing_words: 1,
            extra_words: 0,
            substituted_words: 1,
            total_words: 20,
            reading_speed_wpm: 140,
            completion_percentage: 88,
            semantic_similarity: null,
            keyword_coverage: null,
            analysis_json: null,
            error_message: null,
            created_at: now,
            updated_at: now,
          },
        })}
      />
    )

    expect(screen.getByText("95%")).toBeInTheDocument()
    expect(screen.getByText("140 wpm")).toBeInTheDocument()
  })
})
