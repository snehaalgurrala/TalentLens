import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"

import { CampaignsTable } from "./campaigns-table"
import type { Campaign } from "@/types"

jest.mock("@/services/campaign.service", () => ({
  campaignService: {
    update: jest.fn(),
    remove: jest.fn(),
    create: jest.fn(),
  },
}))
jest.mock("@/services/candidate.service", () => ({
  candidateService: { listRankings: jest.fn() },
}))
jest.mock("@/services/organization.service", () => ({
  organizationService: { listMembers: jest.fn().mockResolvedValue([]) },
}))

const CAMPAIGN: Campaign = {
  id: "c1",
  org_id: "o1",
  created_by: "u1",
  title: "Senior Backend Engineer",
  description: null,
  status: "ACTIVE",
  is_deleted: false,
  created_at: "2026-06-01T00:00:00Z",
  updated_at: "2026-06-02T00:00:00Z",
  job_title: "Backend Engineer II",
  department: "Engineering",
  hiring_manager_id: null,
  recruiter_id: null,
  employment_type: "FULL_TIME",
  location: "Remote",
  experience_min_years: 3,
  experience_max_years: 7,
  salary_min: 100000,
  salary_max: 140000,
  openings_count: 2,
  priority: "HIGH",
  closing_date: null,
  hiring_manager: null,
  recruiter: null,
  resume_count: 12,
  processing_resume_count: 3,
}

function noop() {}

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe("CampaignsTable", () => {
  it("shows an empty state when there are no campaigns", () => {
    renderWithClient(
      <CampaignsTable
        campaigns={[]}
        isLoading={false}
        selectedIds={new Set()}
        onToggleSelect={noop}
        onToggleSelectAll={noop}
        onRowClick={noop}
        onSortChange={noop}
      />
    )
    expect(screen.getByText("No campaigns yet")).toBeInTheDocument()
  })

  it("renders campaign rows with name, department, status, and processing badge", () => {
    renderWithClient(
      <CampaignsTable
        campaigns={[CAMPAIGN]}
        isLoading={false}
        selectedIds={new Set()}
        onToggleSelect={noop}
        onToggleSelectAll={noop}
        onRowClick={noop}
        onSortChange={noop}
      />
    )

    expect(screen.getByText("Senior Backend Engineer")).toBeInTheDocument()
    expect(screen.getByText("Backend Engineer II")).toBeInTheDocument()
    expect(screen.getByText("Engineering")).toBeInTheDocument()
    expect(screen.getByText("Active")).toBeInTheDocument()
    expect(screen.getByText("12")).toBeInTheDocument()
    expect(screen.getByText("Processing (3)")).toBeInTheDocument()
  })

  it("calls onRowClick when a row is clicked", () => {
    const onRowClick = jest.fn()
    renderWithClient(
      <CampaignsTable
        campaigns={[CAMPAIGN]}
        isLoading={false}
        selectedIds={new Set()}
        onToggleSelect={noop}
        onToggleSelectAll={noop}
        onRowClick={onRowClick}
        onSortChange={noop}
      />
    )

    screen.getByText("Senior Backend Engineer").closest("tr")?.click()
    expect(onRowClick).toHaveBeenCalledWith(CAMPAIGN)
  })
})
