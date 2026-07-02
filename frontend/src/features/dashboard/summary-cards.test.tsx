import { render, screen } from "@testing-library/react"

import { SummaryCards } from "./summary-cards"
import type { DashboardSummary } from "@/types"

const SUMMARY: DashboardSummary = {
  total_campaigns: 5,
  active_campaigns: 3,
  closed_campaigns: 2,
  total_candidates: 42,
  processing_candidates: 4,
  shortlisted_candidates: 6,
  rejected_candidates: 1,
  average_match_score: 78.5,
}

describe("SummaryCards", () => {
  it("renders the total campaigns, candidates, and shortlisted counts", () => {
    render(<SummaryCards summary={SUMMARY} />)

    expect(screen.getByText("Total Campaigns")).toBeInTheDocument()
    expect(screen.getByText("5")).toBeInTheDocument()
    expect(screen.getByText("Candidates")).toBeInTheDocument()
    expect(screen.getByText("42")).toBeInTheDocument()
    expect(screen.getByText("Shortlisted")).toBeInTheDocument()
    expect(screen.getByText("6")).toBeInTheDocument()
  })

  it("renders the average match score as a percentage", () => {
    render(<SummaryCards summary={SUMMARY} />)
    expect(screen.getByText("Average Match Score")).toBeInTheDocument()
    expect(screen.getByText("79%")).toBeInTheDocument()
  })

  it("shows a placeholder when there is no match score yet", () => {
    render(<SummaryCards summary={{ ...SUMMARY, average_match_score: null }} />)
    expect(screen.getByText("—")).toBeInTheDocument()
    expect(screen.getByText("No ranked candidates yet")).toBeInTheDocument()
  })
})
