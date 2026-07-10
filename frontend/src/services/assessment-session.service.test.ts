import { api } from "@/services/api"
import { assessmentSessionService } from "@/services/assessment-session.service"

jest.mock("@/services/api", () => ({
  api: { post: jest.fn() },
}))

const mockedPost = api.post as jest.Mock

describe("assessmentSessionService", () => {
  beforeEach(() => {
    mockedPost.mockReset()
    mockedPost.mockResolvedValue({})
  })

  it("createOrResumeSession posts to /assessment/session with the given ids", async () => {
    await assessmentSessionService.createOrResumeSession({
      campaign_id: "campaign-1",
      candidate_id: "candidate-1",
    })

    expect(mockedPost).toHaveBeenCalledWith("/assessment/session", {
      campaign_id: "campaign-1",
      candidate_id: "candidate-1",
    })
  })

  it("uploadRecording posts multipart form data to the recording-type-scoped upload URL", async () => {
    const blob = new Blob(["audio-bytes"], { type: "audio/webm;codecs=opus" })

    await assessmentSessionService.uploadRecording("session-1", "READ_ALOUD", blob, 12.5)

    expect(mockedPost).toHaveBeenCalledTimes(1)
    const [url, formData, config] = mockedPost.mock.calls[0]
    expect(url).toBe("/assessment/session/session-1/recordings/READ_ALOUD/upload")
    expect(formData).toBeInstanceOf(FormData)
    expect((formData as FormData).get("duration_seconds")).toBe("12.5")
    const file = (formData as FormData).get("file") as File
    expect(file.name).toBe("read_aloud.webm")
    expect(config.headers["Content-Type"]).toBe("multipart/form-data")
  })

  it("uploadRecording reports progress via onUploadProgress", async () => {
    const blob = new Blob(["audio-bytes"], { type: "audio/ogg" })
    const onUploadProgress = jest.fn()

    await assessmentSessionService.uploadRecording(
      "session-1",
      "LISTEN_REPEAT",
      blob,
      8,
      onUploadProgress
    )

    const [, , config] = mockedPost.mock.calls[0]
    config.onUploadProgress({ loaded: 50, total: 100 })
    expect(onUploadProgress).toHaveBeenCalledWith(50)
  })

  it("uploadRecording sends X-Assessment-Token when an invitation token is given", async () => {
    const blob = new Blob(["audio-bytes"], { type: "audio/webm" })

    await assessmentSessionService.uploadRecording(
      "session-1",
      "READ_ALOUD",
      blob,
      12.5,
      undefined,
      "invite-token-abc"
    )

    const [, , config] = mockedPost.mock.calls[0]
    expect(config.headers["X-Assessment-Token"]).toBe("invite-token-abc")
  })

  it("uploadRecording omits X-Assessment-Token when there is no invitation token", async () => {
    const blob = new Blob(["audio-bytes"], { type: "audio/webm" })

    await assessmentSessionService.uploadRecording("session-1", "READ_ALOUD", blob, 12.5)

    const [, , config] = mockedPost.mock.calls[0]
    expect(config.headers["X-Assessment-Token"]).toBeUndefined()
  })
})
