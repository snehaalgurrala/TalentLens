import { useMutation, useQueryClient } from "@tanstack/react-query"

import { userService } from "@/services/user.service"
import { useUserStore } from "@/store/user-store"
import type { ApiError, ChangePasswordRequest, User, UserProfileUpdate } from "@/types"

export function useUpdateProfile() {
  const queryClient = useQueryClient()
  const { setUser } = useUserStore()
  return useMutation<User, ApiError, UserProfileUpdate>({
    mutationFn: (data) => userService.updateMe(data),
    onSuccess: (user) => {
      setUser(user)
      void queryClient.invalidateQueries()
    },
  })
}

export function useChangePassword() {
  return useMutation<void, ApiError, ChangePasswordRequest>({
    mutationFn: (data) => userService.changePassword(data),
  })
}
