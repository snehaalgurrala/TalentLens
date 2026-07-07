import { act, render, screen } from "@testing-library/react"

import { AssessmentRunnerProvider, useAssessmentRunner } from "./assessment-runner-context"

function makeRecording() {
  return {
    blob: new Blob(["audio"], { type: "audio/webm" }),
    url: "blob:fake-url",
    durationSeconds: 5,
    mimeType: "audio/webm",
  }
}

function TestConsumer() {
  const runner = useAssessmentRunner()
  return (
    <div>
      <span data-testid="session-id">{runner.sessionId ?? "none"}</span>
      <span data-testid="read-aloud-status">{runner.readAloudUpload.status}</span>
      <span data-testid="read-aloud-progress">{runner.readAloudUpload.progress}</span>
      <span data-testid="listen-repeat-status">{runner.listenRepeatUpload.status}</span>
      <button onClick={() => runner.setSessionId("session-123")}>set-session</button>
      <button onClick={() => runner.setReadAloudRecording(makeRecording())}>set-recording</button>
      <button onClick={() => runner.updateReadAloudUpload({ status: "uploading", progress: 40 })}>
        start-upload
      </button>
      <button
        onClick={() =>
          runner.updateListenRepeatUpload({ status: "failed", error: "network error" })
        }
      >
        fail-upload
      </button>
      <button onClick={() => runner.resetAssessment()}>reset</button>
    </div>
  )
}

function renderRunner() {
  return render(
    <AssessmentRunnerProvider>
      <TestConsumer />
    </AssessmentRunnerProvider>
  )
}

describe("AssessmentRunnerProvider upload state", () => {
  const originalRevokeObjectURL = URL.revokeObjectURL

  beforeEach(() => {
    URL.revokeObjectURL = jest.fn()
  })

  afterEach(() => {
    URL.revokeObjectURL = originalRevokeObjectURL
  })

  it("starts with no session and idle upload state", () => {
    renderRunner()
    expect(screen.getByTestId("session-id")).toHaveTextContent("none")
    expect(screen.getByTestId("read-aloud-status")).toHaveTextContent("idle")
    expect(screen.getByTestId("listen-repeat-status")).toHaveTextContent("idle")
  })

  it("setSessionId updates the session id", () => {
    renderRunner()
    act(() => screen.getByText("set-session").click())
    expect(screen.getByTestId("session-id")).toHaveTextContent("session-123")
  })

  it("updateReadAloudUpload patches only the given fields", () => {
    renderRunner()
    act(() => screen.getByText("start-upload").click())
    expect(screen.getByTestId("read-aloud-status")).toHaveTextContent("uploading")
    expect(screen.getByTestId("read-aloud-progress")).toHaveTextContent("40")
  })

  it("resetAssessment clears sessionId and both upload states back to idle", () => {
    renderRunner()
    act(() => screen.getByText("set-session").click())
    act(() => screen.getByText("set-recording").click())
    act(() => screen.getByText("start-upload").click())
    act(() => screen.getByText("fail-upload").click())

    expect(screen.getByTestId("session-id")).toHaveTextContent("session-123")
    expect(screen.getByTestId("read-aloud-status")).toHaveTextContent("uploading")
    expect(screen.getByTestId("listen-repeat-status")).toHaveTextContent("failed")

    act(() => screen.getByText("reset").click())

    expect(screen.getByTestId("session-id")).toHaveTextContent("none")
    expect(screen.getByTestId("read-aloud-status")).toHaveTextContent("idle")
    expect(screen.getByTestId("read-aloud-progress")).toHaveTextContent("0")
    expect(screen.getByTestId("listen-repeat-status")).toHaveTextContent("idle")
  })
})
