import { render, screen } from "@testing-library/react"

import { ProcessingMonitor } from "./processing-monitor"
import type { CampaignProcessingStatus } from "@/types"

const STATUS: CampaignProcessingStatus = {
  uploaded_count: 2,
  parsing_count: 1,
  embedding_count: 1,
  ready_for_ranking_count: 5,
  completed_count: 5,
  failed_count: 1,
  total_count: 10,
}

describe("ProcessingMonitor", () => {
  it("shows a loading skeleton while isLoading is true", () => {
    const { container } = render(<ProcessingMonitor status={undefined} isLoading />)
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0)
  })

  it("shows an empty message when no resumes have been uploaded", () => {
    render(
      <ProcessingMonitor
        status={{ ...STATUS, uploaded_count: 0, parsing_count: 0, embedding_count: 0, ready_for_ranking_count: 0, completed_count: 0, failed_count: 0, total_count: 0 }}
        isLoading={false}
      />
    )
    expect(screen.getByText(/no resumes uploaded yet/i)).toBeInTheDocument()
  })

  it("renders stage counts and a failed-files callout", () => {
    render(<ProcessingMonitor status={STATUS} isLoading={false} />)

    expect(screen.getByText("Uploaded / Queued")).toBeInTheDocument()
    expect(screen.getByText("Parsing")).toBeInTheDocument()
    expect(screen.getByText("Embedding")).toBeInTheDocument()
    expect(screen.getByText("Ranking Ready")).toBeInTheDocument()
    expect(screen.getByText("Completed")).toBeInTheDocument()
    expect(screen.getByText(/1 file failed processing/i)).toBeInTheDocument()
  })
})
