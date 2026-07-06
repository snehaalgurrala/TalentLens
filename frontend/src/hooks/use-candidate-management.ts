import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { candidateService } from "@/services/candidate.service"
import { campaignKeys } from "@/hooks/use-campaigns"
import { dashboardKeys } from "@/hooks/use-dashboard"
import { rankingKeys } from "@/hooks/use-rankings"
import type {
  ApiError,
  BulkActionResult,
  CandidateListFilters,
  CandidateListResponse,
  PipelineStage,
  ResumeFile,
} from "@/types"

export const candidateManagementKeys = {
  all: ["candidate-management"] as const,
  list: (campaignId: string, filters?: CandidateListFilters) =>
    [...candidateManagementKeys.all, "list", campaignId, filters ?? {}] as const,
}

export function useCampaignCandidates(campaignId: string | undefined, filters?: CandidateListFilters) {
  return useQuery<CandidateListResponse, ApiError>({
    queryKey: candidateManagementKeys.list(campaignId ?? "", filters),
    queryFn: () => candidateService.listCampaignCandidates(campaignId as string, filters),
    enabled: Boolean(campaignId),
  })
}

function useInvalidateAfterMutation() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: candidateManagementKeys.all })
    void queryClient.invalidateQueries({ queryKey: rankingKeys.all })
    void queryClient.invalidateQueries({ queryKey: campaignKeys.all })
    void queryClient.invalidateQueries({ queryKey: dashboardKeys.all })
  }
}

export function useUpdatePipelineStage() {
  const invalidate = useInvalidateAfterMutation()
  return useMutation<ResumeFile, ApiError, { resumeFileId: string; pipelineStage: PipelineStage }>({
    mutationFn: ({ resumeFileId, pipelineStage }) =>
      candidateService.updatePipelineStage(resumeFileId, pipelineStage),
    onSuccess: invalidate,
  })
}

export function useAssignRecruiter() {
  const invalidate = useInvalidateAfterMutation()
  return useMutation<ResumeFile, ApiError, { resumeFileId: string; recruiterId: string | null }>({
    mutationFn: ({ resumeFileId, recruiterId }) =>
      candidateService.assignRecruiter(resumeFileId, recruiterId),
    onSuccess: invalidate,
  })
}

export function useUpdateNotes() {
  const invalidate = useInvalidateAfterMutation()
  return useMutation<ResumeFile, ApiError, { resumeFileId: string; notes: string | null }>({
    mutationFn: ({ resumeFileId, notes }) => candidateService.updateNotes(resumeFileId, notes),
    onSuccess: invalidate,
  })
}

export function useShortlistCandidate() {
  const invalidate = useInvalidateAfterMutation()
  return useMutation<ResumeFile, ApiError, string>({
    mutationFn: (resumeFileId) => candidateService.shortlistCandidate(resumeFileId),
    onSuccess: invalidate,
  })
}

export function useRejectCandidate() {
  const invalidate = useInvalidateAfterMutation()
  return useMutation<ResumeFile, ApiError, string>({
    mutationFn: (resumeFileId) => candidateService.rejectCandidate(resumeFileId),
    onSuccess: invalidate,
  })
}

export function useDeleteCandidate() {
  const invalidate = useInvalidateAfterMutation()
  return useMutation<void, ApiError, string>({
    mutationFn: (resumeFileId) => candidateService.deleteCandidate(resumeFileId),
    onSuccess: invalidate,
  })
}

export function useBulkShortlist() {
  const invalidate = useInvalidateAfterMutation()
  return useMutation<BulkActionResult, ApiError, string[]>({
    mutationFn: (resumeFileIds) => candidateService.bulkShortlist(resumeFileIds),
    onSuccess: invalidate,
  })
}

export function useBulkReject() {
  const invalidate = useInvalidateAfterMutation()
  return useMutation<BulkActionResult, ApiError, string[]>({
    mutationFn: (resumeFileIds) => candidateService.bulkReject(resumeFileIds),
    onSuccess: invalidate,
  })
}

export function useBulkAssignRecruiter() {
  const invalidate = useInvalidateAfterMutation()
  return useMutation<BulkActionResult, ApiError, { resumeFileIds: string[]; recruiterId: string | null }>({
    mutationFn: ({ resumeFileIds, recruiterId }) =>
      candidateService.bulkAssignRecruiter(resumeFileIds, recruiterId),
    onSuccess: invalidate,
  })
}

export function useBulkDeleteCandidates() {
  const invalidate = useInvalidateAfterMutation()
  return useMutation<BulkActionResult, ApiError, string[]>({
    mutationFn: (resumeFileIds) => candidateService.bulkDelete(resumeFileIds),
    onSuccess: invalidate,
  })
}

export function useArchiveCandidate() {
  const invalidate = useInvalidateAfterMutation()
  return useMutation<ResumeFile, ApiError, string>({
    mutationFn: (resumeFileId) => candidateService.archiveCandidate(resumeFileId),
    onSuccess: invalidate,
  })
}

export function useRestoreCandidate() {
  const invalidate = useInvalidateAfterMutation()
  return useMutation<ResumeFile, ApiError, string>({
    mutationFn: (resumeFileId) => candidateService.restoreCandidate(resumeFileId),
    onSuccess: invalidate,
  })
}

export function useBulkArchive() {
  const invalidate = useInvalidateAfterMutation()
  return useMutation<BulkActionResult, ApiError, string[]>({
    mutationFn: (resumeFileIds) => candidateService.bulkArchive(resumeFileIds),
    onSuccess: invalidate,
  })
}

export function useBulkRestore() {
  const invalidate = useInvalidateAfterMutation()
  return useMutation<BulkActionResult, ApiError, string[]>({
    mutationFn: (resumeFileIds) => candidateService.bulkRestore(resumeFileIds),
    onSuccess: invalidate,
  })
}

export function useBulkUpdatePipelineStage() {
  const invalidate = useInvalidateAfterMutation()
  return useMutation<BulkActionResult, ApiError, { resumeFileIds: string[]; pipelineStage: PipelineStage }>({
    mutationFn: ({ resumeFileIds, pipelineStage }) =>
      candidateService.bulkUpdatePipelineStage(resumeFileIds, pipelineStage),
    onSuccess: invalidate,
  })
}
