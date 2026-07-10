import { render, screen } from "@testing-library/react"

import type { AssessmentSessionFull } from "@/types"

import { AssessmentTimeline } from "./assessment-timeline"

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

describe("AssessmentTimeline", () => {
  it("marks only the started step as done when nothing else has happened", () => {
    render(<AssessmentTimeline sessionFull={makeSessionFull()} />)

    expect(screen.getByText("Assessment Started")).toBeInTheDocument()
    const pendingLabels = screen.getAllByText("Pending")
    expect(pendingLabels).toHaveLength(6)
  })

  it("renders a labeled list with an accessible name", () => {
    render(<AssessmentTimeline sessionFull={makeSessionFull()} />)

    expect(screen.getByRole("list", { name: "Assessment processing timeline" })).toBeInTheDocument()
  })
})
