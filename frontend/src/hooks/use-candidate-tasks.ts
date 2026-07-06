import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { candidateProfileKeys } from "@/hooks/use-candidate-profile"
import {
  candidateService,
  type CreateTaskPayload,
  type UpdateTaskPayload,
} from "@/services/candidate.service"
import type { ApiError, CandidateTask } from "@/types"

export const candidateTaskKeys = {
  all: ["candidate-tasks"] as const,
  list: (id: string) => [...candidateTaskKeys.all, "list", id] as const,
}

export function useCandidateTasks(id: string | undefined) {
  return useQuery<CandidateTask[], ApiError>({
    queryKey: candidateTaskKeys.list(id ?? ""),
    queryFn: () => candidateService.listTasks(id as string),
    enabled: Boolean(id),
  })
}

function useInvalidateTasksAndActivity(id: string) {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: candidateTaskKeys.list(id) })
    void queryClient.invalidateQueries({ queryKey: candidateProfileKeys.activity(id) })
  }
}

export function useCreateCandidateTask(id: string) {
  const invalidate = useInvalidateTasksAndActivity(id)
  return useMutation<CandidateTask, ApiError, CreateTaskPayload>({
    mutationFn: (data) => candidateService.createTask(id, data),
    onSuccess: invalidate,
  })
}

export function useUpdateCandidateTask(id: string) {
  const invalidate = useInvalidateTasksAndActivity(id)
  return useMutation<CandidateTask, ApiError, { taskId: string; data: UpdateTaskPayload }>({
    mutationFn: ({ taskId, data }) => candidateService.updateTask(id, taskId, data),
    onSuccess: invalidate,
  })
}

export function useCompleteCandidateTask(id: string) {
  const invalidate = useInvalidateTasksAndActivity(id)
  return useMutation<CandidateTask, ApiError, string>({
    mutationFn: (taskId) => candidateService.completeTask(id, taskId),
    onSuccess: invalidate,
  })
}

export function useReassignCandidateTask(id: string) {
  const invalidate = useInvalidateTasksAndActivity(id)
  return useMutation<CandidateTask, ApiError, { taskId: string; assigneeId: string | null }>({
    mutationFn: ({ taskId, assigneeId }) => candidateService.reassignTask(id, taskId, assigneeId),
    onSuccess: invalidate,
  })
}

export function useDeleteCandidateTask(id: string) {
  const invalidate = useInvalidateTasksAndActivity(id)
  return useMutation<void, ApiError, string>({
    mutationFn: (taskId) => candidateService.deleteTask(id, taskId),
    onSuccess: invalidate,
  })
}
