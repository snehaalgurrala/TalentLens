import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"

import { campaignService } from "@/services/campaign.service"
import type { Campaign } from "@/types"

import { CampaignsListView } from "./campaigns-list-view"

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}))
jest.mock("@/services/campaign.service", () => ({
  campaignService: { list: jest.fn(), create: jest.fn(), update: jest.fn(), remove: jest.fn() },
}))
jest.mock("@/services/candidate.service", () => ({
  candidateService: { listRankings: jest.fn() },
}))
jest.mock("@/services/organization.service", () => ({
  organizationService: { listMembers: jest.fn().mockResolvedValue([]) },
}))

const mockedCampaignService = jest.mocked(campaignService)

const CAMPAIGN: Campaign = {
  id: "c1",
  org_id: "o1",
  created_by: "u1",
  title: "Senior Backend Engineer",
  description: null,
  status: "ACTIVE",
  is_deleted: false,
  created_at: "2026-06-01T00:00:00Z",
  updated_at: "2026-06-01T00:00:00Z",
  job_title: null,
  department: null,
  hiring_manager_id: null,
  recruiter_id: null,
  employment_type: null,
  location: null,
  experience_min_years: null,
  experience_max_years: null,
  salary_min: null,
  salary_max: null,
  openings_count: 1,
  priority: "MEDIUM",
  closing_date: null,
  hiring_manager: null,
  recruiter: null,
  resume_count: 4,
  processing_resume_count: 0,
}

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe("CampaignsListView", () => {
  afterEach(() => {
    jest.clearAllMocks()
  })

  it("fetches and renders campaigns from the real service contract", async () => {
    mockedCampaignService.list.mockResolvedValue([CAMPAIGN])
    renderWithClient(<CampaignsListView />)

    await waitFor(() => expect(screen.getByText("Senior Backend Engineer")).toBeInTheDocument())
    expect(mockedCampaignService.list).toHaveBeenCalled()
  })

  it("debounces search input into a filtered list request", async () => {
    mockedCampaignService.list.mockResolvedValue([CAMPAIGN])
    renderWithClient(<CampaignsListView />)
    await waitFor(() => expect(mockedCampaignService.list).toHaveBeenCalledTimes(1))

    fireEvent.change(screen.getByPlaceholderText("Search campaigns..."), {
      target: { value: "backend" },
    })

    await waitFor(
      () =>
        expect(mockedCampaignService.list).toHaveBeenLastCalledWith(
          expect.objectContaining({ search: "backend" })
        ),
      { timeout: 2000 }
    )
  })

  it("opens the create campaign dialog", async () => {
    mockedCampaignService.list.mockResolvedValue([])
    renderWithClient(<CampaignsListView />)
    await waitFor(() => expect(mockedCampaignService.list).toHaveBeenCalled())

    fireEvent.click(screen.getByRole("button", { name: /new campaign/i }))

    expect(
      await screen.findByText("Set up a new hiring campaign to start collecting resumes.")
    ).toBeInTheDocument()
  })

  it("archives selected campaigns via the bulk actions bar", async () => {
    mockedCampaignService.list.mockResolvedValue([CAMPAIGN])
    mockedCampaignService.update.mockResolvedValue({ ...CAMPAIGN, status: "ARCHIVED" })
    renderWithClient(<CampaignsListView />)
    await waitFor(() => expect(screen.getByText("Senior Backend Engineer")).toBeInTheDocument())

    fireEvent.click(screen.getByRole("checkbox", { name: /select senior backend engineer/i }))
    expect(await screen.findByText("1 selected")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Archive" }))

    await waitFor(() =>
      expect(mockedCampaignService.update).toHaveBeenCalledWith("c1", { status: "ARCHIVED" })
    )
  })
})
