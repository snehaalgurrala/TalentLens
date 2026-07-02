import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"

import { dashboardService } from "@/services/dashboard.service"
import type {
  DashboardActivityItem,
  DashboardSummary,
  ProcessingStatus,
  RecentCampaign,
  TopCandidate,
} from "@/types"

import { DashboardView } from "./dashboard-view"

jest.mock("@/services/dashboard.service", () => ({
  dashboardService: {
    getSummary: jest.fn(),
    getRecentCampaigns: jest.fn(),
    getTopCandidates: jest.fn(),
    getProcessingStatus: jest.fn(),
    getActivity: jest.fn(),
  },
}))

const mockedDashboardService = jest.mocked(dashboardService)

const SUMMARY: DashboardSummary = {
  total_campaigns: 2,
  active_campaigns: 1,
  closed_campaigns: 1,
  total_candidates: 10,
  processing_candidates: 2,
  shortlisted_candidates: 3,
  rejected_candidates: 1,
  average_match_score: 80,
}

const RECENT_CAMPAIGNS: RecentCampaign[] = [
  { id: "c1", title: "Senior Backend Engineer", status: "ACTIVE", created_at: "2026-06-01T00:00:00Z", candidate_count: 5 },
]

const TOP_CANDIDATES: TopCandidate[] = [
  {
    candidate_id: "cand1",
    candidate_name: "Jane Doe",
    resume_file_id: "rf1",
    match_score: 91,
    campaign_id: "c1",
    campaign_name: "Senior Backend Engineer",
    years_of_experience: 5,
    current_company: "Acme",
    review_status: "PENDING",
  },
]

const PROCESSING_STATUS: ProcessingStatus = {
  parsing_queue: 1,
  embedding_queue: 0,
  ranking_queue: 2,
  failed_jobs: 0,
  completed_jobs: 8,
}

const ACTIVITY: DashboardActivityItem[] = [
  {
    id: "campaign-created:c1",
    type: "CAMPAIGN_CREATED",
    description: 'Campaign "Senior Backend Engineer" was created.',
    occurred_at: new Date().toISOString(),
    campaign_id: "c1",
    campaign_name: "Senior Backend Engineer",
  },
]

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

function mockAllSuccess() {
  mockedDashboardService.getSummary.mockResolvedValue(SUMMARY)
  mockedDashboardService.getRecentCampaigns.mockResolvedValue(RECENT_CAMPAIGNS)
  mockedDashboardService.getTopCandidates.mockResolvedValue(TOP_CANDIDATES)
  mockedDashboardService.getProcessingStatus.mockResolvedValue(PROCESSING_STATUS)
  mockedDashboardService.getActivity.mockResolvedValue(ACTIVITY)
}

describe("DashboardView", () => {
  afterEach(() => {
    jest.clearAllMocks()
  })

  it("fetches and renders real data from every dashboard endpoint", async () => {
    mockAllSuccess()
    renderWithClient(<DashboardView />)

    await waitFor(() => expect(screen.getAllByText("Senior Backend Engineer").length).toBeGreaterThan(0))

    expect(mockedDashboardService.getSummary).toHaveBeenCalled()
    expect(mockedDashboardService.getRecentCampaigns).toHaveBeenCalledWith(5)
    expect(mockedDashboardService.getTopCandidates).toHaveBeenCalledWith(6)
    expect(mockedDashboardService.getProcessingStatus).toHaveBeenCalled()
    expect(mockedDashboardService.getActivity).toHaveBeenCalledWith(12)

    expect(screen.getByText("Jane Doe")).toBeInTheDocument()
    expect(screen.getByText('Campaign "Senior Backend Engineer" was created.')).toBeInTheDocument()
  })

  it("shows an error state with a working retry button when a request fails", async () => {
    mockAllSuccess()
    mockedDashboardService.getSummary.mockRejectedValue({ status: 500, message: "Server error" })

    renderWithClient(<DashboardView />)

    await waitFor(() => expect(screen.getAllByText("Backend is offline").length).toBeGreaterThan(0))

    mockedDashboardService.getSummary.mockResolvedValue(SUMMARY)
    fireEvent.click(screen.getAllByRole("button", { name: /retry/i })[0])

    await waitFor(() => expect(screen.getByText("Total Campaigns")).toBeInTheDocument())
  })
})
