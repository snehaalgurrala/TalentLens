import { api } from "@/services/api"
import { assessmentDashboardService } from "@/services/assessment-dashboard.service"
import { apiClient } from "@/services/axios"

jest.mock("@/services/api", () => ({
  api: { get: jest.fn() },
}))

jest.mock("@/services/axios", () => ({
  apiClient: { get: jest.fn() },
}))

const mockedGet = api.get as jest.Mock
const mockedApiClientGet = apiClient.get as jest.Mock

describe("assessmentDashboardService", () => {
  beforeEach(() => {
    mockedGet.mockReset()
    mockedApiClientGet.mockReset()
  })

  it("getFull fetches the aggregate dashboard payload for a session", async () => {
    mockedGet.mockResolvedValue({})

    await assessmentDashboardService.getFull("session-1")

    expect(mockedGet).toHaveBeenCalledWith("/assessment/session/session-1/full")
  })

  it("getSessionByCandidate fetches by candidate id with campaign_id as a query param", async () => {
    mockedGet.mockResolvedValue({})

    await assessmentDashboardService.getSessionByCandidate("candidate-1", "campaign-1")

    expect(mockedGet).toHaveBeenCalledWith("/assessment/session/by-candidate/candidate-1", {
      params: { campaign_id: "campaign-1" },
    })
  })

  it("downloadRecording fetches the recording as a blob and returns its mime type", async () => {
    const blob = new Blob(["audio-bytes"], { type: "audio/webm" })
    mockedApiClientGet.mockResolvedValue({ data: blob, headers: { "content-type": "audio/webm" } })

    const result = await assessmentDashboardService.downloadRecording("session-1", "READ_ALOUD")

    expect(mockedApiClientGet).toHaveBeenCalledWith(
      "/assessment/session/session-1/recordings/READ_ALOUD/download",
      { responseType: "blob" }
    )
    expect(result.blob).toBe(blob)
    expect(result.mimeType).toBe("audio/webm")
  })
})
