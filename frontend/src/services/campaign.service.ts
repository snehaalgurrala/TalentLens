import { api } from "@/services/api"
import type {
  Campaign,
  CampaignCreate,
  CampaignFilters,
  CampaignProcessingStatus,
  CampaignSummary,
  CampaignUpdate,
} from "@/types"

export const campaignService = {
  list: (params?: CampaignFilters) => api.get<Campaign[]>("/campaigns/", { params }),
  get: (campaignId: string) => api.get<Campaign>(`/campaigns/${campaignId}`),
  create: (data: CampaignCreate) => api.post<Campaign>("/campaigns/", data),
  update: (campaignId: string, data: CampaignUpdate) =>
    api.patch<Campaign>(`/campaigns/${campaignId}`, data),
  remove: (campaignId: string) => api.delete<void>(`/campaigns/${campaignId}`),
  getSummary: (campaignId: string) =>
    api.get<CampaignSummary>(`/campaigns/${campaignId}/summary`),
  getProcessingStatus: (campaignId: string) =>
    api.get<CampaignProcessingStatus>(`/campaigns/${campaignId}/processing-status`),
}
