import { render, screen } from "@testing-library/react"

import type { AssessmentSessionFull } from "@/types"

import { ProcessingStatusBadges } from "./processing-status-badges"

const now = new Date().toISOString()

function makeSessionFull(overrides: Partial<AssessmentSessionFull> = {}): AssessmentSessionFull {
  return {
    session: {
      id: "session-1",
      org_id: "org-1",
      campaign_id: "camp-1",
      candidate_id: "cand-1",
      current_section: "APTITUDE",
      current_question: 1,
      status: "IN_PROGRESS",
      started_at: now,
      completed_at: null,
      created_at: now,
      updated_at: now,
    },
    candidate: { id: "cand-1", first_name: "Jane", last_name: "Doe", email: "jane@example.com" },
    campaign: { id: "camp-1", title: "Frontend Engineer" },
    pipeline_stage: null,
    recordings: [],
    communication_assessment: null,
    ...overrides,
  }
}

describe("ProcessingStatusBadges", () => {
  it("shows every stage as pending when nothing has happened yet", () => {
    render(<ProcessingStatusBadges sessionFull={makeSessionFull()} />)

    expect(screen.getByText("Uploaded Pending")).toBeInTheDocument()
    expect(screen.getByText("Transcribed Pending")).toBeInTheDocument()
    expect(screen.getByText("Analyzed Pending")).toBeInTheDocument()
    expect(screen.getByText("Completed Pending")).toBeInTheDocument()
  })

  it("shows Uploaded as done once every recording is UPLOADED", () => {
    render(
      <ProcessingStatusBadges
        sessionFull={makeSessionFull({
          recordings: [
            {
              recording: {
                id: "r1",
                session_id: "session-1",
                recording_type: "READ_ALOUD",
                filename: "clip.webm",
                mime_type: "audio/webm",
                duration_seconds: 10,
                storage_path: "x/y.webm",
                file_size: 100,
                status: "UPLOADED",
                uploaded_at: now,
                created_at: now,
                updated_at: now,
              },
              reference_sentence: "Reference.",
              transcript: null,
              analysis: null,
            },
          ],
        })}
      />
    )

    expect(screen.getByText("Uploaded")).toBeInTheDocument()
    expect(screen.getByText("Transcribed Pending")).toBeInTheDocument()
  })
})
