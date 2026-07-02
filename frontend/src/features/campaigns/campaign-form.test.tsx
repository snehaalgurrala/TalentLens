import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"

import { campaignService } from "@/services/campaign.service"
import type { Campaign } from "@/types"

import { CampaignForm } from "./campaign-form"

jest.mock("@/services/campaign.service", () => ({
  campaignService: { create: jest.fn(), update: jest.fn() },
}))
jest.mock("@/services/organization.service", () => ({
  organizationService: { listMembers: jest.fn().mockResolvedValue([]) },
}))

const mockedCampaignService = jest.mocked(campaignService)

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe("CampaignForm", () => {
  afterEach(() => {
    jest.clearAllMocks()
  })

  it("shows a validation error when the campaign name is empty", async () => {
    renderWithClient(<CampaignForm mode="create" open onOpenChange={jest.fn()} />)

    fireEvent.click(screen.getByRole("button", { name: /create campaign/i }))

    await waitFor(() => expect(screen.getByText("Campaign name is required")).toBeInTheDocument())
    expect(mockedCampaignService.create).not.toHaveBeenCalled()
  })

  it("submits a create request with the entered campaign name", async () => {
    mockedCampaignService.create.mockResolvedValue({ id: "c1" } as Campaign)
    const onOpenChange = jest.fn()
    renderWithClient(<CampaignForm mode="create" open onOpenChange={onOpenChange} />)

    fireEvent.change(screen.getByLabelText("Campaign Name"), {
      target: { value: "Senior Backend Engineer" },
    })
    fireEvent.click(screen.getByRole("button", { name: /create campaign/i }))

    await waitFor(() => expect(mockedCampaignService.create).toHaveBeenCalled())
    const payload = mockedCampaignService.create.mock.calls[0][0]
    expect(payload.title).toBe("Senior Backend Engineer")
    expect(payload.status).toBe("DRAFT")
    expect(payload.priority).toBe("MEDIUM")
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false))
  })

  it("submits an update request when editing an existing campaign", async () => {
    const campaign: Campaign = {
      id: "c1",
      org_id: "o1",
      created_by: "u1",
      title: "Old Title",
      description: null,
      status: "DRAFT",
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
      resume_count: 0,
      processing_resume_count: 0,
    }
    mockedCampaignService.update.mockResolvedValue(campaign)
    renderWithClient(<CampaignForm mode="edit" campaign={campaign} open onOpenChange={jest.fn()} />)

    fireEvent.change(screen.getByLabelText("Campaign Name"), {
      target: { value: "New Title" },
    })
    fireEvent.click(screen.getByRole("button", { name: /save changes/i }))

    await waitFor(() => expect(mockedCampaignService.update).toHaveBeenCalledWith("c1", expect.objectContaining({ title: "New Title" })))
  })
})
