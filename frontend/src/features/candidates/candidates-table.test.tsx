import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"

import type { CandidateListItem } from "@/types"

import { CandidatesTable } from "./candidates-table"

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
  skills: ["Python", "SQL", "AWS", "Docker"],
  education: [{ institution: "MIT", degree: "BS", field: "Computer Science" }],
  rank: 1,
  overall_score: 88,
  sub_scores: {
    semantic_score: 90,
    skills_score: 85,
    experience_score: 100,
    education_score: 80,
    projects_score: 70,
    certification_score: 60,
  },
  recommendation: "Strong Match",
  upload_status: "PARSED",
  review_status: "PENDING",
  pipeline_stage: "RANKED",
  assigned_recruiter: null,
  notes: null,
  applied_at: "2026-06-01T00:00:00Z",
}

function noop() {}

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe("CandidatesTable", () => {
  it("shows an empty state when there are no candidates", () => {
    renderWithClient(
      <CandidatesTable
        candidates={[]}
        isLoading={false}
        rankingAvailable
        selectedIds={new Set()}
        onToggleSelect={noop}
        onToggleSelectAll={noop}
        onEditNotes={noop}
        onSortChange={noop}
      />
    )
    expect(screen.getByText("No candidates yet")).toBeInTheDocument()
  })

  it("renders candidate rows with name, company, score, skills, and badges", () => {
    renderWithClient(
      <CandidatesTable
        candidates={[CANDIDATE]}
        isLoading={false}
        rankingAvailable
        selectedIds={new Set()}
        onToggleSelect={noop}
        onToggleSelectAll={noop}
        onEditNotes={noop}
        onSortChange={noop}
      />
    )

    expect(screen.getByText("Jane Doe")).toBeInTheDocument()
    expect(screen.getByText("Acme Corp")).toBeInTheDocument()
    expect(screen.getByText("88%")).toBeInTheDocument()
    expect(screen.getByText("Strong Match")).toBeInTheDocument()
    expect(screen.getByText("Ranked")).toBeInTheDocument()
    expect(screen.getByText("Python")).toBeInTheDocument()
    expect(screen.getByText("+1")).toBeInTheDocument()
  })

  it("hides scores when ranking is not available for the campaign", () => {
    renderWithClient(
      <CandidatesTable
        candidates={[{ ...CANDIDATE, overall_score: null, recommendation: null }]}
        isLoading={false}
        rankingAvailable={false}
        selectedIds={new Set()}
        onToggleSelect={noop}
        onToggleSelectAll={noop}
        onEditNotes={noop}
        onSortChange={noop}
      />
    )
    expect(screen.queryByText("88%")).not.toBeInTheDocument()
  })

  it("calls onRowClick when a row is clicked", () => {
    const onRowClick = jest.fn()
    renderWithClient(
      <CandidatesTable
        candidates={[CANDIDATE]}
        isLoading={false}
        rankingAvailable
        selectedIds={new Set()}
        onToggleSelect={noop}
        onToggleSelectAll={noop}
        onEditNotes={noop}
        onRowClick={onRowClick}
        onSortChange={noop}
      />
    )

    screen.getByText("Jane Doe").closest("tr")?.click()
    expect(onRowClick).toHaveBeenCalledWith(CANDIDATE)
  })

  it("calls onToggleSelect when a row checkbox is clicked", () => {
    const onToggleSelect = jest.fn()
    renderWithClient(
      <CandidatesTable
        candidates={[CANDIDATE]}
        isLoading={false}
        rankingAvailable
        selectedIds={new Set()}
        onToggleSelect={onToggleSelect}
        onToggleSelectAll={noop}
        onEditNotes={noop}
        onSortChange={noop}
      />
    )

    screen.getByRole("checkbox", { name: "Select Jane Doe" }).click()
    expect(onToggleSelect).toHaveBeenCalledWith("rf1")
  })
})
