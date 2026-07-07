import { api } from "@/services/api"
import { apiClient } from "@/services/axios"
import type { AssessmentSession, AssessmentSessionFull, RecordingType } from "@/types"

export const assessmentDashboardService = {
  getFull: (sessionId: string) =>
    api.get<AssessmentSessionFull>(`/assessment/session/${sessionId}/full`),

  getSessionByCandidate: (candidateId: string, campaignId: string) =>
    api.get<AssessmentSession>(`/assessment/session/by-candidate/${candidateId}`, {
      params: { campaign_id: campaignId },
    }),

  downloadRecording: async (
    sessionId: string,
    recordingType: RecordingType
  ): Promise<{ blob: Blob; mimeType: string }> => {
    const response = await apiClient.get<Blob>(
      `/assessment/session/${sessionId}/recordings/${recordingType}/download`,
      { responseType: "blob" }
    )
    return { blob: response.data, mimeType: String(response.headers["content-type"] ?? "audio/webm") }
  },
}
