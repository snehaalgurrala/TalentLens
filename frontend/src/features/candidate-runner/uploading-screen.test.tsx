import * as React from "react"
import { act, render, screen, waitFor } from "@testing-library/react"

import { AssessmentRunnerProvider, useAssessmentRunner } from "./assessment-runner-context"
import { UploadingScreen } from "./uploading-screen"

const pushMock = jest.fn()

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}))

const mutateAsyncMock = jest.fn()

jest.mock("@/hooks/use-assessment-session", () => ({
  useUploadRecording: () => ({ mutateAsync: mutateAsyncMock }),
}))

const markCompletedMutateMock = jest.fn()

jest.mock("@/hooks/use-assessment-invitations", () => ({
  useMarkInvitationCompleted: () => ({ mutate: markCompletedMutateMock }),
}))

function makeRecording() {
  return {
    blob: new Blob(["audio"], { type: "audio/webm" }),
    url: "blob:fake-url",
    durationSeconds: 5,
    mimeType: "audio/webm",
  }
}

function Seed({
  withRecordings = true,
  invitationToken = null,
}: {
  withRecordings?: boolean
  invitationToken?: string | null
}) {
  const { setSessionId, setInvitationToken, setReadAloudRecording, setListenRepeatRecording } =
    useAssessmentRunner()
  React.useEffect(() => {
    setSessionId("session-123")
    if (invitationToken) setInvitationToken(invitationToken)
    if (withRecordings) {
      setReadAloudRecording(makeRecording())
      setListenRepeatRecording(makeRecording())
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  return null
}

function renderScreen(withRecordings = true, invitationToken: string | null = null) {
  return render(
    <AssessmentRunnerProvider>
      <Seed withRecordings={withRecordings} invitationToken={invitationToken} />
      <UploadingScreen />
    </AssessmentRunnerProvider>
  )
}

describe("UploadingScreen", () => {
  const originalRevokeObjectURL = URL.revokeObjectURL

  beforeEach(() => {
    URL.revokeObjectURL = jest.fn()
    mutateAsyncMock.mockReset()
    mutateAsyncMock.mockResolvedValue(undefined)
    pushMock.mockReset()
    markCompletedMutateMock.mockReset()
  })

  afterEach(() => {
    URL.revokeObjectURL = originalRevokeObjectURL
  })

  it("shows a 'session not found' message when there is no session id", () => {
    render(
      <AssessmentRunnerProvider>
        <UploadingScreen />
      </AssessmentRunnerProvider>
    )
    expect(screen.getByText("Session Not Found")).toBeInTheDocument()
    expect(mutateAsyncMock).not.toHaveBeenCalled()
  })

  it("triggers an upload for both recordings once a session and recordings exist", async () => {
    renderScreen()
    await waitFor(() => expect(mutateAsyncMock).toHaveBeenCalledTimes(2))

    const recordingTypes = mutateAsyncMock.mock.calls.map(([vars]) => vars.recordingType)
    expect(recordingTypes.sort()).toEqual(["LISTEN_REPEAT", "READ_ALOUD"])
  })

  it("navigates to /assessment/completed once both uploads succeed", async () => {
    renderScreen()
    await waitFor(() => expect(mutateAsyncMock).toHaveBeenCalledTimes(2))

    // Real timers: the resolved mutateAsync promises must actually settle
    // (microtask queue) before the screen's own 600ms completion timeout
    // starts, so faking timers here would race the promise resolution
    // rather than the setTimeout.
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/assessment/completed"), {
      timeout: 2000,
    })
  })

  it("passes the invitation token through to the upload call itself", async () => {
    renderScreen(true, "invite-token-abc")
    await waitFor(() => expect(mutateAsyncMock).toHaveBeenCalledTimes(2))

    for (const [vars] of mutateAsyncMock.mock.calls) {
      expect(vars.invitationToken).toBe("invite-token-abc")
    }
  })

  it("reports the invitation as completed when an invitation token is present", async () => {
    renderScreen(true, "invite-token-abc")
    await waitFor(() => expect(mutateAsyncMock).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(markCompletedMutateMock).toHaveBeenCalledWith("invite-token-abc"))
  })

  it("does not report completion when there is no invitation token (dev-testing flow)", async () => {
    renderScreen(true, null)
    await waitFor(() => expect(mutateAsyncMock).toHaveBeenCalledTimes(2))

    expect(markCompletedMutateMock).not.toHaveBeenCalled()
  })

  it("shows Retry on failure and re-invokes only that recording's upload", async () => {
    mutateAsyncMock.mockImplementation((vars) =>
      vars.recordingType === "READ_ALOUD"
        ? Promise.reject({ message: "network error", status: 0 })
        : Promise.resolve()
    )

    renderScreen()
    await waitFor(() => expect(mutateAsyncMock).toHaveBeenCalledTimes(2))

    const retryButtons = await screen.findAllByText("Retry")
    expect(retryButtons).toHaveLength(1)

    mutateAsyncMock.mockClear()
    mutateAsyncMock.mockResolvedValue(undefined)
    act(() => retryButtons[0].click())

    await waitFor(() => expect(mutateAsyncMock).toHaveBeenCalledTimes(1))
    expect(mutateAsyncMock.mock.calls[0][0].recordingType).toBe("READ_ALOUD")
  })
})
