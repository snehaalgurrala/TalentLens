import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"

import { assessmentDashboardService } from "@/services/assessment-dashboard.service"
import type { AssessmentSession } from "@/types"

import { AssessmentTab } from "./assessment-tab"

jest.mock("@/services/assessment-dashboard.service", () => ({
  assessmentDashboardService: { getSessionByCandidate: jest.fn() },
}))

const mockedService = jest.mocked(assessmentDashboardService)

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe("AssessmentTab", () => {
  afterEach(() => jest.clearAllMocks())

  it("renders an empty state when the candidate hasn't started an assessment", async () => {
    mockedService.getSessionByCandidate.mockRejectedValue({
      status: 404,
      message: "No assessment session found for this candidate in this campaign.",
    })

    renderWithClient(<AssessmentTab candidateId="cand1" campaignId="camp1" />)

    expect(
      await screen.findByText("Assessment not started for this candidate yet")
    ).toBeInTheDocument()
  })

  it("renders a summary and link to the full assessment when a session exists", async () => {
    const session: AssessmentSession = {
      id: "session-1",
      org_id: "org-1",
      campaign_id: "camp1",
      candidate_id: "cand1",
      current_section: "READ_ALOUD",
      current_question: null,
      status: "IN_PROGRESS",
      started_at: new Date().toISOString(),
      completed_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    mockedService.getSessionByCandidate.mockResolvedValue(session)

    renderWithClient(<AssessmentTab candidateId="cand1" campaignId="camp1" />)

    expect(await screen.findByText("In Progress")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /View Full Assessment/i })).toHaveAttribute(
      "href",
      "/assessments/session-1"
    )
  })
})
