import { api, toApiError } from "@/services/api"
import { apiClient } from "@/services/axios"
import type {
  BulkActionResult,
  CandidateListFilters,
  CandidateListResponse,
  CandidateRanking,
  PipelineStage,
  ResumeFile,
  UploadResponse,
} from "@/types"

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
  downloadResume: async (resumeId: string): Promise<{ blob: Blob; filename: string }> => {
    try {
      const response = await apiClient.get<Blob>(`/resumes/${resumeId}/download`, {
        responseType: "blob",
      })
      const disposition = String(response.headers["content-disposition"] ?? "")
      const match = /filename="([^"]*)"/.exec(disposition)
      return { blob: response.data, filename: match?.[1] ?? "resume" }
    } catch (error) {
      throw toApiError(error)
    }
  },

  listCampaignCandidates: (campaignId: string, filters?: CandidateListFilters) =>
    api.get<CandidateListResponse>(`/campaigns/${campaignId}/candidates`, { params: filters }),

  updatePipelineStage: (resumeFileId: string, pipelineStage: PipelineStage) =>
    api.patch<ResumeFile>(`/candidates/${resumeFileId}/pipeline-stage`, {
      pipeline_stage: pipelineStage,
    }),
  assignRecruiter: (resumeFileId: string, assignedRecruiterId: string | null) =>
    api.patch<ResumeFile>(`/candidates/${resumeFileId}/recruiter`, {
      assigned_recruiter_id: assignedRecruiterId,
    }),
  updateNotes: (resumeFileId: string, notes: string | null) =>
    api.patch<ResumeFile>(`/candidates/${resumeFileId}/notes`, { notes }),
  shortlistCandidate: (resumeFileId: string) =>
    api.post<ResumeFile>(`/candidates/${resumeFileId}/shortlist`),
  rejectCandidate: (resumeFileId: string) =>
    api.post<ResumeFile>(`/candidates/${resumeFileId}/reject`),
  deleteCandidate: (resumeFileId: string) => api.delete<void>(`/candidates/${resumeFileId}`),

  bulkShortlist: (resumeFileIds: string[]) =>
    api.post<BulkActionResult>(`/candidates/bulk/shortlist`, { resume_file_ids: resumeFileIds }),
  bulkReject: (resumeFileIds: string[]) =>
    api.post<BulkActionResult>(`/candidates/bulk/reject`, { resume_file_ids: resumeFileIds }),
  bulkAssignRecruiter: (resumeFileIds: string[], assignedRecruiterId: string | null) =>
    api.post<BulkActionResult>(`/candidates/bulk/assign-recruiter`, {
      resume_file_ids: resumeFileIds,
      assigned_recruiter_id: assignedRecruiterId,
    }),
  bulkDelete: (resumeFileIds: string[]) =>
    api.post<BulkActionResult>(`/candidates/bulk/delete`, { resume_file_ids: resumeFileIds }),
}
