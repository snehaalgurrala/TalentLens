import * as React from "react"
import { render, screen } from "@testing-library/react"

import { AssessmentRunnerProvider, useAssessmentRunner } from "./assessment-runner-context"
import { InstructionsScreen } from "./instructions-screen"

const pushMock = jest.fn()

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}))

const markStartedMutateMock = jest.fn()

jest.mock("@/hooks/use-assessment-invitations", () => ({
  useMarkInvitationStarted: () => ({ mutate: markStartedMutateMock }),
}))

function Seed({ invitationToken }: { invitationToken: string | null }) {
  const { setInvitationToken } = useAssessmentRunner()
  React.useEffect(() => {
    if (invitationToken) setInvitationToken(invitationToken)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  return null
}

function renderScreen(invitationToken: string | null = null) {
  return render(
    <AssessmentRunnerProvider>
      <Seed invitationToken={invitationToken} />
      <InstructionsScreen />
    </AssessmentRunnerProvider>
  )
}

describe("InstructionsScreen", () => {
  beforeEach(() => {
    pushMock.mockReset()
    markStartedMutateMock.mockReset()
  })

  it("navigates to the first aptitude question on Continue", () => {
    renderScreen()
    screen.getByText("Continue").click()
    expect(pushMock).toHaveBeenCalledWith("/assessment/aptitude/1")
  })

  it("reports the invitation as started when an invitation token is present", () => {
    renderScreen("invite-token-abc")
    screen.getByText("Continue").click()
    expect(markStartedMutateMock).toHaveBeenCalledWith("invite-token-abc")
    expect(pushMock).toHaveBeenCalledWith("/assessment/aptitude/1")
  })

  it("does not report a start when there is no invitation token (dev-testing flow)", () => {
    renderScreen(null)
    screen.getByText("Continue").click()
    expect(markStartedMutateMock).not.toHaveBeenCalled()
    expect(pushMock).toHaveBeenCalledWith("/assessment/aptitude/1")
  })
})
