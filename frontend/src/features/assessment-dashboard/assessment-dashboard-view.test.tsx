import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"

import { assessmentDashboardService } from "@/services/assessment-dashboard.service"
import type { AssessmentSessionFull } from "@/types"

import { AssessmentDashboardView } from "./assessment-dashboard-view"

jest.mock("@/services/assessment-dashboard.service", () => ({
  assessmentDashboardService: { getFull: jest.fn(), downloadRecording: jest.fn() },
}))

const mockedService = jest.mocked(assessmentDashboardService)

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

const now = new Date().toISOString()

function makeSessionFull(): AssessmentSessionFull {
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
  }
}

describe("AssessmentDashboardView", () => {
  afterEach(() => jest.clearAllMocks())

  it("renders an error state when the request fails", async () => {
    mockedService.getFull.mockRejectedValue({ status: 500, message: "Server error" })

    renderWithClient(<AssessmentDashboardView sessionId="session-1" />)

    expect(await screen.findByText("Backend is offline")).toBeInTheDocument()
  })

  it("renders the summary and processing status once data loads", async () => {
    mockedService.getFull.mockResolvedValue(makeSessionFull())

    renderWithClient(<AssessmentDashboardView sessionId="session-1" />)

    expect(await screen.findByText("Assessment Summary")).toBeInTheDocument()
    expect(screen.getByText("AI Processing Status")).toBeInTheDocument()
    expect(screen.getByText("Timeline")).toBeInTheDocument()
  })
})
