import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"

import { assessmentInvitationService } from "@/services/assessment-invitation.service"
import { campaignService } from "@/services/campaign.service"
import { candidateService } from "@/services/candidate.service"
import type { Campaign, CandidateListItem, CandidateListResponse } from "@/types"

import { CandidatesListView } from "./candidates-list-view"

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}))
jest.mock("@/services/campaign.service", () => ({
  campaignService: { list: jest.fn() },
}))
jest.mock("@/services/candidate.service", () => ({
  candidateService: {
    listCampaignCandidates: jest.fn(),
    updatePipelineStage: jest.fn(),
    assignRecruiter: jest.fn(),
    updateNotes: jest.fn(),
    shortlistCandidate: jest.fn(),
    rejectCandidate: jest.fn(),
    deleteCandidate: jest.fn(),
    bulkShortlist: jest.fn(),
    bulkReject: jest.fn(),
    bulkAssignRecruiter: jest.fn(),
    bulkDelete: jest.fn(),
    downloadResume: jest.fn(),
  },
}))
jest.mock("@/services/organization.service", () => ({
  organizationService: { listMembers: jest.fn().mockResolvedValue([]) },
}))
jest.mock("@/services/assessment-invitation.service", () => ({
  assessmentInvitationService: { send: jest.fn() },
}))

const mockedCampaignService = jest.mocked(campaignService)
const mockedCandidateService = jest.mocked(candidateService)
const mockedAssessmentInvitationService = jest.mocked(assessmentInvitationService)

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
  resume_count: 1,
  processing_resume_count: 0,
}

const CANDIDATE: CandidateListItem = {
  resume_file_id: "rf1",
  candidate_id: "cand1",
  candidate_name: "Jane Doe",
  email: "jane@example.com",
  phone: null,
  location: null,
  current_company: "Acme Corp",
  current_role: "Senior Engineer",
  years_of_experience: 6,
  skills: ["Python"],
  education: [],
  rank: 1,
  overall_score: 88,
  sub_scores: null,
  recommendation: "Strong Match",
  upload_status: "PARSED",
  review_status: "PENDING",
  pipeline_stage: "RANKED",
  assigned_recruiter: null,
  notes: null,
  applied_at: "2026-06-01T00:00:00Z",
}

const CANDIDATE_LIST_RESPONSE: CandidateListResponse = {
  items: [CANDIDATE],
  total: 1,
  skip: 0,
  limit: 20,
  ranking_available: true,
}

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe("CandidatesListView", () => {
  afterEach(() => {
    jest.clearAllMocks()
    window.sessionStorage.clear()
  })

  it("defaults to the most recent campaign and renders its candidates", async () => {
    mockedCampaignService.list.mockResolvedValue([CAMPAIGN])
    mockedCandidateService.listCampaignCandidates.mockResolvedValue(CANDIDATE_LIST_RESPONSE)

    renderWithClient(<CandidatesListView />)

    await waitFor(() => expect(screen.getAllByText("Jane Doe").length).toBeGreaterThan(0))
    expect(mockedCandidateService.listCampaignCandidates).toHaveBeenCalledWith(
      "c1",
      expect.objectContaining({ sort_by: "overall_score" })
    )
  })

  it("debounces search input into a filtered candidate request", async () => {
    mockedCampaignService.list.mockResolvedValue([CAMPAIGN])
    mockedCandidateService.listCampaignCandidates.mockResolvedValue(CANDIDATE_LIST_RESPONSE)
    renderWithClient(<CandidatesListView />)
    await waitFor(() => expect(screen.getAllByText("Jane Doe").length).toBeGreaterThan(0))

    fireEvent.change(screen.getByPlaceholderText(/search name, email, phone/i), {
      target: { value: "jane" },
    })

    await waitFor(
      () =>
        expect(mockedCandidateService.listCampaignCandidates).toHaveBeenLastCalledWith(
          "c1",
          expect.objectContaining({ search: "jane" })
        ),
      { timeout: 2000 }
    )
  })

  it("shows a banner when ranking is not available for the campaign", async () => {
    mockedCampaignService.list.mockResolvedValue([CAMPAIGN])
    mockedCandidateService.listCampaignCandidates.mockResolvedValue({
      ...CANDIDATE_LIST_RESPONSE,
      ranking_available: false,
    })
    renderWithClient(<CandidatesListView />)

    expect(await screen.findByText(/see AI match scores and recommendations/i)).toBeInTheDocument()
  })

  it("bulk shortlists selected candidates via the bulk actions bar", async () => {
    mockedCampaignService.list.mockResolvedValue([CAMPAIGN])
    mockedCandidateService.listCampaignCandidates.mockResolvedValue(CANDIDATE_LIST_RESPONSE)
    mockedCandidateService.bulkShortlist.mockResolvedValue({ succeeded: ["rf1"], failed: [] })
    renderWithClient(<CandidatesListView />)
    await waitFor(() => expect(screen.getAllByText("Jane Doe").length).toBeGreaterThan(0))

    fireEvent.click(screen.getAllByRole("checkbox", { name: "Select Jane Doe" })[0])
    expect(await screen.findByText("1 selected")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Shortlist" }))

    await waitFor(() => expect(mockedCandidateService.bulkShortlist).toHaveBeenCalledWith(["rf1"]))
  })

  it("sends an assessment invitation to the selected candidate via the Send Assessment dialog", async () => {
    mockedCampaignService.list.mockResolvedValue([CAMPAIGN])
    mockedCandidateService.listCampaignCandidates.mockResolvedValue(CANDIDATE_LIST_RESPONSE)
    mockedAssessmentInvitationService.send.mockResolvedValue({
      succeeded: [{ candidate_id: "cand1", invitation_id: "inv1" }],
      failed: [],
    })
    renderWithClient(<CandidatesListView />)
    await waitFor(() => expect(screen.getAllByText("Jane Doe").length).toBeGreaterThan(0))

    fireEvent.click(screen.getAllByRole("checkbox", { name: "Select Jane Doe" })[0])
    expect(await screen.findByText("1 selected")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Send Assessment" }))
    const sendButtons = await screen.findAllByRole("button", { name: "Send Assessment" })
    fireEvent.click(sendButtons[sendButtons.length - 1])

    await waitFor(() =>
      expect(mockedAssessmentInvitationService.send).toHaveBeenCalledWith({
        campaign_id: "c1",
        candidate_ids: ["cand1"],
        expiration_hours: 48,
      })
    )

    fireEvent.click(await screen.findByRole("button", { name: "Done" }))
    expect(screen.queryByText("1 selected")).not.toBeInTheDocument()
  })
})
