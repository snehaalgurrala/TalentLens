import { render, screen } from "@testing-library/react"

import { AssessmentRunnerProvider, useAssessmentRunner } from "./assessment-runner-context"
import { InvitationEntryScreen } from "./invitation-entry-screen"

const replaceMock = jest.fn()

jest.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
}))

const refetchMock = jest.fn()
let queryState: {
  data?: { assessment_session: { id: string; status: string } }
  isError: boolean
  error?: { status: number; message: string }
} = { isError: false }

jest.mock("@/hooks/use-assessment-invitations", () => ({
  useInvitationByToken: () => ({ ...queryState, refetch: refetchMock }),
}))

function ContextSpy() {
  const { sessionId, invitationToken } = useAssessmentRunner()
  return (
    <div>
      <span data-testid="session-id">{sessionId ?? "none"}</span>
      <span data-testid="invitation-token">{invitationToken ?? "none"}</span>
    </div>
  )
}

function renderScreen() {
  return render(
    <AssessmentRunnerProvider>
      <ContextSpy />
      <InvitationEntryScreen token="tok-123" />
    </AssessmentRunnerProvider>
  )
}

describe("InvitationEntryScreen", () => {
  beforeEach(() => {
    replaceMock.mockReset()
    refetchMock.mockReset()
    queryState = { isError: false }
  })

  it("shows a validating message while the token is pending", () => {
    renderScreen()
    expect(screen.getByText("Validating Your Invitation")).toBeInTheDocument()
  })

  it("stores the session id and token, then navigates to device-check on success", () => {
    queryState = {
      isError: false,
      data: { assessment_session: { id: "session-abc", status: "IN_PROGRESS" } },
    }
    renderScreen()

    expect(screen.getByTestId("session-id")).toHaveTextContent("session-abc")
    expect(screen.getByTestId("invitation-token")).toHaveTextContent("tok-123")
    expect(replaceMock).toHaveBeenCalledWith("/assessment/device-check")
  })

  it("shows an invalid-link message for a 404", () => {
    queryState = { isError: true, error: { status: 404, message: "Invitation not found." } }
    renderScreen()
    expect(screen.getByText("Invalid Assessment Link")).toBeInTheDocument()
  })

  it("shows a revoked message for a 410 with 'revoked' in the detail", () => {
    queryState = {
      isError: true,
      error: { status: 410, message: "This invitation has been revoked." },
    }
    renderScreen()
    expect(screen.getByText("Invitation Revoked")).toBeInTheDocument()
  })

  it("shows an expired message for a 410 with 'expired' in the detail", () => {
    queryState = { isError: true, error: { status: 410, message: "This invitation has expired." } }
    renderScreen()
    expect(screen.getByText("Assessment Link Expired")).toBeInTheDocument()
  })

  it("shows a completed message for a 410 with 'completed' in the detail", () => {
    queryState = {
      isError: true,
      error: { status: 410, message: "This assessment has already been completed." },
    }
    renderScreen()
    expect(screen.getByText("Assessment Already Completed")).toBeInTheDocument()
  })

  it("shows a retry button for a network failure", () => {
    queryState = { isError: true, error: { status: 0, message: "Network Error" } }
    renderScreen()
    expect(screen.getByText("Something Went Wrong")).toBeInTheDocument()
    screen.getByText("Try Again").click()
    expect(refetchMock).toHaveBeenCalled()
  })
})
