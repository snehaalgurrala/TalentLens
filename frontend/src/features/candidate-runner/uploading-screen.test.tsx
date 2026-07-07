import * as React from "react"
import { act, render, screen, waitFor } from "@testing-library/react"

import { AssessmentRunnerProvider, useAssessmentRunner } from "./assessment-runner-context"
import { UploadingScreen } from "./uploading-screen"

const pushMock = jest.fn()

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}))

const mutateMock = jest.fn()

jest.mock("@/hooks/use-assessment-session", () => ({
  useUploadRecording: () => ({ mutate: mutateMock }),
}))

function makeRecording() {
  return {
    blob: new Blob(["audio"], { type: "audio/webm" }),
    url: "blob:fake-url",
    durationSeconds: 5,
    mimeType: "audio/webm",
  }
}

function Seed({ withRecordings = true }: { withRecordings?: boolean }) {
  const { setSessionId, setReadAloudRecording, setListenRepeatRecording } = useAssessmentRunner()
  React.useEffect(() => {
    setSessionId("session-123")
    if (withRecordings) {
      setReadAloudRecording(makeRecording())
      setListenRepeatRecording(makeRecording())
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  return null
}

function renderScreen(withRecordings = true) {
  return render(
    <AssessmentRunnerProvider>
      <Seed withRecordings={withRecordings} />
      <UploadingScreen />
    </AssessmentRunnerProvider>
  )
}

describe("UploadingScreen", () => {
  const originalRevokeObjectURL = URL.revokeObjectURL

  beforeEach(() => {
    URL.revokeObjectURL = jest.fn()
    mutateMock.mockReset()
    pushMock.mockReset()
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
    expect(mutateMock).not.toHaveBeenCalled()
  })

  it("triggers an upload for both recordings once a session and recordings exist", async () => {
    renderScreen()
    await waitFor(() => expect(mutateMock).toHaveBeenCalledTimes(2))

    const recordingTypes = mutateMock.mock.calls.map(([vars]) => vars.recordingType)
    expect(recordingTypes.sort()).toEqual(["LISTEN_REPEAT", "READ_ALOUD"])
  })

  it("navigates to /assessment/completed once both uploads succeed", async () => {
    mutateMock.mockImplementation((vars, { onSuccess }) => onSuccess())

    jest.useFakeTimers()
    renderScreen()
    await waitFor(() => expect(mutateMock).toHaveBeenCalledTimes(2))

    act(() => {
      jest.advanceTimersByTime(700)
    })

    expect(pushMock).toHaveBeenCalledWith("/assessment/completed")
    jest.useRealTimers()
  })

  it("shows Retry on failure and re-invokes only that recording's upload", async () => {
    mutateMock.mockImplementation((vars, { onError }) => {
      if (vars.recordingType === "READ_ALOUD") onError({ message: "network error", status: 0 })
    })

    renderScreen()
    await waitFor(() => expect(mutateMock).toHaveBeenCalledTimes(2))

    const retryButtons = await screen.findAllByText("Retry")
    expect(retryButtons).toHaveLength(1)

    mutateMock.mockClear()
    act(() => retryButtons[0].click())

    await waitFor(() => expect(mutateMock).toHaveBeenCalledTimes(1))
    expect(mutateMock.mock.calls[0][0].recordingType).toBe("READ_ALOUD")
  })
})
