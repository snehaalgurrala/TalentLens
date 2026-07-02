import { api } from "@/services/api"
import type {
  DashboardActivityItem,
  DashboardSummary,
  ProcessingStatus,
  RecentCampaign,
  TopCandidate,
} from "@/types"

export const dashboardService = {
  getSummary: () => api.get<DashboardSummary>("/dashboard/summary"),
  getRecentCampaigns: (limit?: number) =>
    api.get<RecentCampaign[]>("/dashboard/recent-campaigns", { params: { limit } }),
  getTopCandidates: (limit?: number) =>
    api.get<TopCandidate[]>("/dashboard/top-candidates", { params: { limit } }),
  getProcessingStatus: () => api.get<ProcessingStatus>("/dashboard/processing-status"),
  getActivity: (limit?: number) =>
    api.get<DashboardActivityItem[]>("/dashboard/activity", { params: { limit } }),
}
