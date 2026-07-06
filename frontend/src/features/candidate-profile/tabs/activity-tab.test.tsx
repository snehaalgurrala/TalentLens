import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"

import { candidateService } from "@/services/candidate.service"
import type { CandidateActivity } from "@/types"

import { ActivityTab } from "./activity-tab"

jest.mock("@/services/candidate.service", () => ({
  candidateService: { listActivity: jest.fn() },
}))

const mockedCandidateService = jest.mocked(candidateService)

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe("ActivityTab", () => {
  afterEach(() => jest.clearAllMocks())

  it("renders an empty state when there is no activity", async () => {
    mockedCandidateService.listActivity.mockResolvedValue([])
    renderWithClient(<ActivityTab candidateId="cand1" />)

    expect(await screen.findByText("No activity yet")).toBeInTheDocument()
  })

  it("renders timeline events with human-readable labels", async () => {
    const events: CandidateActivity[] = [
      {
        id: "a1",
        event_type: "SHORTLISTED",
        actor: { id: "u1", full_name: "Jane Recruiter", email: "jane@example.com", role: "RECRUITER" },
        event_metadata: null,
        created_at: new Date().toISOString(),
      },
      {
        id: "a2",
        event_type: "PIPELINE_STAGE_CHANGED",
        actor: { id: "u1", full_name: "Jane Recruiter", email: "jane@example.com", role: "RECRUITER" },
        event_metadata: { from_stage: "RANKED", to_stage: "HIRED" },
        created_at: new Date().toISOString(),
      },
      {
        id: "a3",
        event_type: "RESUME_UPLOADED",
        actor: null,
        event_metadata: null,
        created_at: new Date().toISOString(),
      },
    ]
    mockedCandidateService.listActivity.mockResolvedValue(events)
    renderWithClient(<ActivityTab candidateId="cand1" />)

    expect(await screen.findByText("Shortlisted")).toBeInTheDocument()
    expect(screen.getByText("Hired")).toBeInTheDocument()
    expect(screen.getByText("Resume uploaded")).toBeInTheDocument()
  })
})
