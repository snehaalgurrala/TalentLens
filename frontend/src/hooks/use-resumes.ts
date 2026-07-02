import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import type { Query } from "@tanstack/react-query"

import { candidateService } from "@/services/candidate.service"
import { campaignKeys } from "@/hooks/use-campaigns"
import type { ApiError, ResumeFile, UploadResponse } from "@/types"

const ACTIVE_UPLOAD_STATUSES = new Set(["PENDING", "UPLOADED", "PROCESSING"])
const REFETCH_INTERVAL_MS = 15_000

export const resumeKeys = {
  all: ["resumes"] as const,
  list: (campaignId: string) => [...resumeKeys.all, "list", campaignId] as const,
}

function refetchWhileProcessing(query: Query<ResumeFile[], ApiError>): number | false {
  const data = query.state.data
  if (!data || data.length === 0) return false
  return data.some((rf) => ACTIVE_UPLOAD_STATUSES.has(rf.upload_status))
    ? REFETCH_INTERVAL_MS
    : false
}

export function useResumes(campaignId: string | undefined) {
  return useQuery<ResumeFile[], ApiError>({
    queryKey: resumeKeys.list(campaignId ?? ""),
    queryFn: () => candidateService.listResumes(campaignId as string),
    enabled: Boolean(campaignId),
    refetchInterval: refetchWhileProcessing,
  })
}

export function useUploadResumes(campaignId: string) {
  const queryClient = useQueryClient()
  return useMutation<
    UploadResponse,
    ApiError,
    { files: File[]; onUploadProgress?: (percent: number) => void }
  >({
    mutationFn: ({ files, onUploadProgress }) =>
      candidateService.uploadResumes(campaignId, files, onUploadProgress),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: resumeKeys.list(campaignId) })
      void queryClient.invalidateQueries({ queryKey: campaignKeys.all })
    },
  })
}

export function useDeleteResume(campaignId: string) {
  const queryClient = useQueryClient()
  return useMutation<void, ApiError, string>({
    mutationFn: (resumeId) => candidateService.deleteResume(resumeId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: resumeKeys.list(campaignId) })
      void queryClient.invalidateQueries({ queryKey: campaignKeys.all })
    },
  })
}
