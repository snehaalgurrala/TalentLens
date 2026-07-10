import { api } from "@/services/api"
import type { ChangePasswordRequest, User, UserListItem, UserProfileUpdate, UserRole } from "@/types"

export const userService = {
  getMe: () => api.get<User>("/users/me"),
  updateMe: (data: UserProfileUpdate) => api.patch<User>("/users/me", data),
  changePassword: (data: ChangePasswordRequest) =>
    api.post<void>("/users/me/change-password", data),
  listOrgUsers: () => api.get<UserListItem[]>("/users"),
  updateRole: (userId: string, role: UserRole) =>
    api.patch<UserListItem>(`/users/${userId}/role`, { role }),
  deactivate: (userId: string) => api.post<UserListItem>(`/users/${userId}/deactivate`),
  reactivate: (userId: string) => api.post<UserListItem>(`/users/${userId}/reactivate`),
  resetPassword: (userId: string) =>
    api.post<{ token: string }>(`/users/${userId}/reset-password`),
}
