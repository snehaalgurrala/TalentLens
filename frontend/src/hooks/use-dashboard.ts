import { useQuery } from "@tanstack/react-query"

import { dashboardService } from "@/services/dashboard.service"
import type {
  ApiError,
  DashboardActivityItem,
  DashboardSummary,
  ProcessingStatus,
  RecentCampaign,
  TopCandidate,
} from "@/types"

const PROCESSING_STATUS_REFETCH_INTERVAL_MS = 30_000

export const dashboardKeys = {
  all: ["dashboard"] as const,
  summary: () => [...dashboardKeys.all, "summary"] as const,
  recentCampaigns: (limit?: number) => [...dashboardKeys.all, "recent-campaigns", limit] as const,
  topCandidates: (limit?: number) => [...dashboardKeys.all, "top-candidates", limit] as const,
  processingStatus: () => [...dashboardKeys.all, "processing-status"] as const,
  activity: (limit?: number) => [...dashboardKeys.all, "activity", limit] as const,
}

export function useDashboardSummary() {
  return useQuery<DashboardSummary, ApiError>({
    queryKey: dashboardKeys.summary(),
    queryFn: dashboardService.getSummary,
  })
}

export function useRecentCampaigns(limit = 5) {
  return useQuery<RecentCampaign[], ApiError>({
    queryKey: dashboardKeys.recentCampaigns(limit),
    queryFn: () => dashboardService.getRecentCampaigns(limit),
  })
}

export function useTopCandidates(limit = 10) {
  return useQuery<TopCandidate[], ApiError>({
    queryKey: dashboardKeys.topCandidates(limit),
    queryFn: () => dashboardService.getTopCandidates(limit),
  })
}

export function useProcessingStatus() {
  return useQuery<ProcessingStatus, ApiError>({
    queryKey: dashboardKeys.processingStatus(),
    queryFn: dashboardService.getProcessingStatus,
    refetchInterval: PROCESSING_STATUS_REFETCH_INTERVAL_MS,
  })
}

export function useDashboardActivity(limit = 20) {
  return useQuery<DashboardActivityItem[], ApiError>({
    queryKey: dashboardKeys.activity(limit),
    queryFn: () => dashboardService.getActivity(limit),
  })
}
