import { fireEvent, render, screen } from "@testing-library/react"

import { DashboardErrorState } from "./dashboard-error-state"

describe("DashboardErrorState", () => {
  it("shows a network error message when status is 0", () => {
    render(<DashboardErrorState error={{ status: 0, message: "" }} onRetry={jest.fn()} />)
    expect(screen.getByText("Network error")).toBeInTheDocument()
  })

  it("shows an unauthorized message for 401/403", () => {
    render(<DashboardErrorState error={{ status: 403, message: "" }} onRetry={jest.fn()} />)
    expect(screen.getByText("You don't have access to this data")).toBeInTheDocument()
  })

  it("shows a backend offline message for 5xx", () => {
    render(<DashboardErrorState error={{ status: 503, message: "" }} onRetry={jest.fn()} />)
    expect(screen.getByText("Backend is offline")).toBeInTheDocument()
  })

  it("falls back to the error message for other statuses", () => {
    render(<DashboardErrorState error={{ status: 422, message: "Invalid request." }} onRetry={jest.fn()} />)
    expect(screen.getByText("Invalid request.")).toBeInTheDocument()
  })

  it("calls onRetry when the retry button is clicked", () => {
    const onRetry = jest.fn()
    render(<DashboardErrorState error={{ status: 0, message: "" }} onRetry={onRetry} />)

    fireEvent.click(screen.getByRole("button", { name: /retry/i }))

    expect(onRetry).toHaveBeenCalledTimes(1)
  })
})
