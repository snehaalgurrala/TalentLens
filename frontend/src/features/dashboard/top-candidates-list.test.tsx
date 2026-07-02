import { render, screen } from "@testing-library/react"

import { TopCandidatesList } from "./top-candidates-list"
import type { TopCandidate } from "@/types"

const CANDIDATE: TopCandidate = {
  candidate_id: "cand1",
  candidate_name: "Jane Doe",
  resume_file_id: "rf1",
  match_score: 92,
  campaign_id: "c1",
  campaign_name: "Senior Backend Engineer",
  years_of_experience: 6,
  current_company: "Acme",
  review_status: "PENDING",
}

describe("TopCandidatesList", () => {
  it("shows loading skeletons while isLoading is true", () => {
    const { container } = render(<TopCandidatesList candidates={[]} isLoading />)
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0)
  })

  it("shows an empty state when there are no ranked candidates", () => {
    render(<TopCandidatesList candidates={[]} isLoading={false} />)
    expect(screen.getByText("No ranked candidates yet")).toBeInTheDocument()
  })

  it("renders a ranked candidate with name, match score, and rank badge", () => {
    render(<TopCandidatesList candidates={[CANDIDATE]} isLoading={false} />)

    expect(screen.getByText("Jane Doe")).toBeInTheDocument()
    expect(screen.getByText("92%")).toBeInTheDocument()
    expect(screen.getByLabelText("Rank 1")).toBeInTheDocument()
    expect(screen.getByText("Acme")).toBeInTheDocument()
  })
})
