import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"

import type { CandidateListItem } from "@/types"

import { CandidateActionsMenu } from "./candidate-actions-menu"

// Note: Radix's DropdownMenu opens via real PointerEvents, which JSDOM does
// not implement — so the open/click-through flow is covered manually (see
// the `run`/verify skill), mirroring CampaignActionsMenu's test strategy.
jest.mock("@/services/candidate.service", () => ({
  candidateService: {
    updatePipelineStage: jest.fn(),
    assignRecruiter: jest.fn(),
    updateNotes: jest.fn(),
    shortlistCandidate: jest.fn(),
    rejectCandidate: jest.fn(),
    deleteCandidate: jest.fn(),
    downloadResume: jest.fn(),
  },
}))
jest.mock("@/services/organization.service", () => ({
  organizationService: { listMembers: jest.fn().mockResolvedValue([]) },
}))

const CANDIDATE: CandidateListItem = {
  resume_file_id: "rf1",
  candidate_id: "c1",
  candidate_name: "Jane Doe",
  email: "jane@example.com",
  phone: null,
  location: null,
  current_company: "Acme Corp",
  current_role: "Senior Engineer",
  years_of_experience: 6,
  skills: [],
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

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe("CandidateActionsMenu", () => {
  it("renders an accessible actions trigger for the candidate", () => {
    renderWithClient(
      <CandidateActionsMenu candidate={CANDIDATE} onEditNotes={jest.fn()} campaignId="camp1" />
    )
    expect(screen.getByRole("button", { name: "Actions for Jane Doe" })).toBeInTheDocument()
  })
})
