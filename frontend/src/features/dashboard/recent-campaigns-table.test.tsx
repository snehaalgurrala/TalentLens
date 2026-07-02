import { render, screen } from "@testing-library/react"

import { RecentCampaignsTable } from "./recent-campaigns-table"
import type { RecentCampaign } from "@/types"

const CAMPAIGN: RecentCampaign = {
  id: "c1",
  title: "Senior Backend Engineer",
  status: "ACTIVE",
  created_at: "2026-06-01T00:00:00Z",
  candidate_count: 12,
}

describe("RecentCampaignsTable", () => {
  it("shows a loading skeleton while isLoading is true", () => {
    const { container } = render(<RecentCampaignsTable campaigns={[]} isLoading />)
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0)
  })

  it("shows an empty state when there are no campaigns", () => {
    render(<RecentCampaignsTable campaigns={[]} isLoading={false} />)
    expect(screen.getByText("No campaigns yet")).toBeInTheDocument()
  })

  it("renders campaign rows with title, candidate count, and status", () => {
    render(<RecentCampaignsTable campaigns={[CAMPAIGN]} isLoading={false} />)

    expect(screen.getByText("Senior Backend Engineer")).toBeInTheDocument()
    expect(screen.getByText("12")).toBeInTheDocument()
    expect(screen.getByText("ACTIVE")).toBeInTheDocument()
  })
})
