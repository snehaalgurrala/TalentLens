import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { userService } from "@/services/user.service"
import type { ApiError, UserListItem, UserRole } from "@/types"

export const userManagementKeys = {
  all: ["user-management"] as const,
  list: () => [...userManagementKeys.all, "list"] as const,
}

export function useOrgUsers() {
  return useQuery<UserListItem[], ApiError>({
    queryKey: userManagementKeys.list(),
    queryFn: userService.listOrgUsers,
  })
}

export function useUpdateUserRole() {
  const queryClient = useQueryClient()
  return useMutation<UserListItem, ApiError, { userId: string; role: UserRole }>({
    mutationFn: ({ userId, role }) => userService.updateRole(userId, role),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: userManagementKeys.all })
    },
  })
}

export function useDeactivateUser() {
  const queryClient = useQueryClient()
  return useMutation<UserListItem, ApiError, string>({
    mutationFn: (userId) => userService.deactivate(userId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: userManagementKeys.all })
    },
  })
}

export function useReactivateUser() {
  const queryClient = useQueryClient()
  return useMutation<UserListItem, ApiError, string>({
    mutationFn: (userId) => userService.reactivate(userId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: userManagementKeys.all })
    },
  })
}

export function useResetUserPassword() {
  return useMutation<{ token: string }, ApiError, string>({
    mutationFn: (userId) => userService.resetPassword(userId),
  })
}
