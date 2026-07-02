import { render, screen } from "@testing-library/react"

import { ActivityFeed } from "./activity-feed"
import type { DashboardActivityItem } from "@/types"

const EVENT: DashboardActivityItem = {
  id: "campaign-created:1",
  type: "CAMPAIGN_CREATED",
  description: 'Campaign "Senior Backend Engineer" was created.',
  occurred_at: new Date().toISOString(),
  campaign_id: "c1",
  campaign_name: "Senior Backend Engineer",
}

describe("ActivityFeed", () => {
  it("shows loading skeletons while isLoading is true", () => {
    const { container } = render(<ActivityFeed events={[]} isLoading />)
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0)
  })

  it("shows an empty state when there is no activity", () => {
    render(<ActivityFeed events={[]} isLoading={false} />)
    expect(screen.getByText("No activity yet")).toBeInTheDocument()
  })

  it("renders an activity event's description", () => {
    render(<ActivityFeed events={[EVENT]} isLoading={false} />)
    expect(screen.getByText('Campaign "Senior Backend Engineer" was created.')).toBeInTheDocument()
    expect(screen.getByText("Just now")).toBeInTheDocument()
  })
})
