import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { campaignService } from "@/services/campaign.service"
import { organizationService } from "@/services/organization.service"
import type {
  ApiError,
  Campaign,
  CampaignCreate,
  CampaignFilters,
  CampaignProcessingStatus,
  CampaignSummary,
  CampaignUpdate,
  UserSummary,
} from "@/types"

const PROCESSING_STATUS_REFETCH_INTERVAL_MS = 15_000

export const campaignKeys = {
  all: ["campaigns"] as const,
  list: (filters?: CampaignFilters) => [...campaignKeys.all, "list", filters ?? {}] as const,
  detail: (id: string) => [...campaignKeys.all, "detail", id] as const,
  summary: (id: string) => [...campaignKeys.all, "summary", id] as const,
  processingStatus: (id: string) => [...campaignKeys.all, "processing-status", id] as const,
  orgMembers: () => [...campaignKeys.all, "org-members"] as const,
}

export function useCampaigns(filters?: CampaignFilters) {
  return useQuery<Campaign[], ApiError>({
    queryKey: campaignKeys.list(filters),
    queryFn: () => campaignService.list(filters),
  })
}

export function useCampaign(campaignId: string | undefined) {
  return useQuery<Campaign, ApiError>({
    queryKey: campaignKeys.detail(campaignId ?? ""),
    queryFn: () => campaignService.get(campaignId as string),
    enabled: Boolean(campaignId),
  })
}

export function useCampaignSummary(campaignId: string | undefined) {
  return useQuery<CampaignSummary, ApiError>({
    queryKey: campaignKeys.summary(campaignId ?? ""),
    queryFn: () => campaignService.getSummary(campaignId as string),
    enabled: Boolean(campaignId),
  })
}

export function useCampaignProcessingStatus(campaignId: string | undefined) {
  return useQuery<CampaignProcessingStatus, ApiError>({
    queryKey: campaignKeys.processingStatus(campaignId ?? ""),
    queryFn: () => campaignService.getProcessingStatus(campaignId as string),
    enabled: Boolean(campaignId),
    refetchInterval: PROCESSING_STATUS_REFETCH_INTERVAL_MS,
  })
}

export function useOrgMembers() {
  return useQuery<UserSummary[], ApiError>({
    queryKey: campaignKeys.orgMembers(),
    queryFn: organizationService.listMembers,
  })
}

export function useCreateCampaign() {
  const queryClient = useQueryClient()
  return useMutation<Campaign, ApiError, CampaignCreate>({
    mutationFn: (data) => campaignService.create(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: campaignKeys.all })
    },
  })
}

export function useUpdateCampaign(campaignId: string) {
  const queryClient = useQueryClient()
  return useMutation<Campaign, ApiError, CampaignUpdate>({
    mutationFn: (data) => campaignService.update(campaignId, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: campaignKeys.all })
    },
  })
}

export function useDeleteCampaign() {
  const queryClient = useQueryClient()
  return useMutation<void, ApiError, string>({
    mutationFn: (campaignId) => campaignService.remove(campaignId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: campaignKeys.all })
    },
  })
}
