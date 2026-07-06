import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"

import { candidateService } from "@/services/candidate.service"
import type { CandidateProfile } from "@/types"

import { CandidateProfileView } from "./candidate-profile-view"

jest.mock("@/services/candidate.service", () => ({
  candidateService: {
    getProfile: jest.fn(),
    getMatchAnalysis: jest.fn(),
    listNotes: jest.fn(),
    listActivity: jest.fn(),
    updatePipelineStage: jest.fn(),
    assignRecruiter: jest.fn(),
    shortlistCandidate: jest.fn(),
    rejectCandidate: jest.fn(),
    deleteCandidate: jest.fn(),
    downloadResume: jest.fn(),
  },
}))
jest.mock("@/services/organization.service", () => ({
  organizationService: { listMembers: jest.fn().mockResolvedValue([]) },
}))

const mockedCandidateService = jest.mocked(candidateService)

const PROFILE: CandidateProfile = {
  resume_file_id: "rf1",
  candidate_id: "cand1",
  candidate_name: "Jane Doe",
  email: "jane@example.com",
  phone: null,
  location: "Remote",
  linkedin_url: null,
  github_url: null,
  current_company: "Acme Corp",
  current_role: "Senior Engineer",
  years_of_experience: 6,
  structured_resume: {
    skills: ["Python", "SQL"],
    experience: [],
    education: [],
    projects: [],
    certifications: [],
    summary: null,
  },
  parse_confidence: 0.92,
  campaign: { id: "c1", title: "Backend Engineer" },
  upload_status: "PARSED",
  review_status: "PENDING",
  pipeline_stage: "RANKED",
  assigned_recruiter: null,
  uploaded_at: "2026-06-01T00:00:00Z",
  overall_score: 88,
  sub_scores: {
    semantic_score: 80,
    skills_score: 90,
    experience_score: 85,
    education_score: 100,
    projects_score: 70,
    certification_score: 60,
  },
  recommendation: "Strong Match",
  ranking_available: true,
}

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe("CandidateProfileView", () => {
  afterEach(() => jest.clearAllMocks())

  it("shows a loading skeleton before the profile resolves", () => {
    mockedCandidateService.getProfile.mockReturnValue(new Promise(() => {}))
    const { container } = renderWithClient(<CandidateProfileView candidateId="cand1" />)
    expect(container.querySelector('[data-slot="skeleton"]')).toBeInTheDocument()
  })

  it("shows an error state when the profile fails to load", async () => {
    mockedCandidateService.getProfile.mockRejectedValue({
      status: 404,
      message: "Candidate not found.",
    })
    renderWithClient(<CandidateProfileView candidateId="cand1" />)

    expect(await screen.findByRole("alert")).toBeInTheDocument()
  })

  it("renders the header, summary cards, and default overview tab", async () => {
    mockedCandidateService.getProfile.mockResolvedValue(PROFILE)
    renderWithClient(<CandidateProfileView candidateId="cand1" />)

    await waitFor(() => expect(screen.getAllByText("Jane Doe").length).toBeGreaterThan(0))
    expect(screen.getAllByText(/Senior Engineer/).length).toBeGreaterThan(0)
    expect(screen.getAllByText("88%").length).toBeGreaterThan(0)
    expect(screen.getByRole("tab", { name: "Notes" })).toBeInTheDocument()
    // Overview tab content is mounted by default
    expect(screen.getAllByText("jane@example.com").length).toBeGreaterThan(0)
  })

  it("shows a not-yet-ranked message in place of scores when unranked", async () => {
    mockedCandidateService.getProfile.mockResolvedValue({
      ...PROFILE,
      overall_score: null,
      sub_scores: null,
      recommendation: null,
      ranking_available: false,
    })
    renderWithClient(<CandidateProfileView candidateId="cand1" />)

    expect(await screen.findByText(/hasn.t been ranked yet/i)).toBeInTheDocument()
  })
})
