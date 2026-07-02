import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import type { Query } from "@tanstack/react-query"

import { jobDescriptionService } from "@/services/job-description.service"
import { campaignKeys } from "@/hooks/use-campaigns"
import type { ApiError, JobDescription, JobDescriptionCreate } from "@/types"

const REFETCH_INTERVAL_MS = 15_000

export const jobDescriptionKeys = {
  all: ["job-descriptions"] as const,
  list: (campaignId: string) => [...jobDescriptionKeys.all, "list", campaignId] as const,
}

function refetchWhileParsing(query: Query<JobDescription[], ApiError>): number | false {
  const data = query.state.data
  if (!data || data.length === 0) return false
  const active = data.some(
    (jd) =>
      jd.parsing_status === "PENDING" ||
      jd.parsing_status === "PROCESSING" ||
      jd.embedding_status === "PENDING" ||
      jd.embedding_status === "GENERATING"
  )
  return active ? REFETCH_INTERVAL_MS : false
}

export function useJobDescriptions(campaignId: string | undefined) {
  return useQuery<JobDescription[], ApiError>({
    queryKey: jobDescriptionKeys.list(campaignId ?? ""),
    queryFn: () => jobDescriptionService.listByCampaign(campaignId as string),
    enabled: Boolean(campaignId),
    refetchInterval: refetchWhileParsing,
  })
}

export function useCreateJobDescriptionText(campaignId: string) {
  const queryClient = useQueryClient()
  return useMutation<JobDescription, ApiError, JobDescriptionCreate>({
    mutationFn: (data) => jobDescriptionService.createFromText(campaignId, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: jobDescriptionKeys.list(campaignId) })
    },
  })
}

export function useUploadJobDescription(campaignId: string) {
  const queryClient = useQueryClient()
  return useMutation<JobDescription, ApiError, File>({
    mutationFn: (file) => jobDescriptionService.uploadFile(campaignId, file),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: jobDescriptionKeys.list(campaignId) })
    },
  })
}

export function useDeleteJobDescription(campaignId: string) {
  const queryClient = useQueryClient()
  return useMutation<void, ApiError, string>({
    mutationFn: (jobDescriptionId) => jobDescriptionService.remove(jobDescriptionId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: jobDescriptionKeys.list(campaignId) })
      void queryClient.invalidateQueries({ queryKey: campaignKeys.all })
    },
  })
}

export function useDownloadJobDescription() {
  return useMutation<Blob, ApiError, string>({
    mutationFn: (jobDescriptionId) => jobDescriptionService.download(jobDescriptionId),
  })
}
