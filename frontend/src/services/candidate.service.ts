import { api } from "@/services/api"
import type { CandidateRanking, ResumeFile, UploadResponse } from "@/types"

export const candidateService = {
  listRankings: (campaignId: string) =>
    api.get<CandidateRanking[]>(`/campaigns/${campaignId}/rankings`),
  listResumes: (campaignId: string) =>
    api.get<ResumeFile[]>(`/campaigns/${campaignId}/resumes`),
  getResume: (resumeId: string) => api.get<ResumeFile>(`/resumes/${resumeId}`),
  uploadResumes: (campaignId: string, files: File[], onUploadProgress?: (percent: number) => void) => {
    const formData = new FormData()
    for (const file of files) {
      formData.append("files", file)
    }
    return api.post<UploadResponse>(`/campaigns/${campaignId}/resumes/upload`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: onUploadProgress
        ? (event) => {
            if (event.total) onUploadProgress(Math.round((event.loaded / event.total) * 100))
          }
        : undefined,
    })
  },
  deleteResume: (resumeId: string) => api.delete<void>(`/resumes/${resumeId}`),
}
