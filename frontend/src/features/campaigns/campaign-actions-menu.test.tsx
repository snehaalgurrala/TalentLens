import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"

import type { Campaign } from "@/types"

import { CampaignActionsMenu } from "./campaign-actions-menu"

// Note: Radix's DropdownMenu opens via real PointerEvents, which JSDOM does
// not implement — so the open/click-through flow is covered manually (see
// the `run`/verify skill) and via the equivalent bulk-action buttons in
// campaigns-list-view.test.tsx, which use plain click handlers.
jest.mock("@/services/campaign.service", () => ({
  campaignService: { create: jest.fn(), update: jest.fn(), remove: jest.fn() },
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

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe("CampaignActionsMenu", () => {
  it("renders an accessible actions trigger for the campaign", () => {
    renderWithClient(<CampaignActionsMenu campaign={CAMPAIGN} />)
    expect(
      screen.getByRole("button", { name: "Actions for Senior Backend Engineer" })
    ).toBeInTheDocument()
  })
})
