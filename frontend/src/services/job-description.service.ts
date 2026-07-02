import { api } from "@/services/api"
import type { JobDescription, JobDescriptionCreate } from "@/types"

export const jobDescriptionService = {
  createFromText: (campaignId: string, data: JobDescriptionCreate) =>
    api.post<JobDescription>(`/campaigns/${campaignId}/job-descriptions`, data),
  uploadFile: (campaignId: string, file: File) => {
    const formData = new FormData()
    formData.append("file", file)
    return api.post<JobDescription>(`/campaigns/${campaignId}/job-descriptions/upload`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
  },
  get: (jobDescriptionId: string) =>
    api.get<JobDescription>(`/job-descriptions/${jobDescriptionId}`),
  listByCampaign: (campaignId: string) =>
    api.get<JobDescription[]>(`/campaigns/${campaignId}/job-descriptions`),
  remove: (jobDescriptionId: string) => api.delete<void>(`/job-descriptions/${jobDescriptionId}`),
  download: (jobDescriptionId: string) =>
    api.get<Blob>(`/job-descriptions/${jobDescriptionId}/download`, { responseType: "blob" }),
}
