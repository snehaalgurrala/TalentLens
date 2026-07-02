import { api } from "@/services/api"
import type { AppNotification, PaginationParams } from "@/types"

export const notificationService = {
  list: (params?: PaginationParams) => api.get<AppNotification[]>("/notifications/", { params }),
  markRead: (notificationId: string) =>
    api.patch<AppNotification>(`/notifications/${notificationId}`, { is_read: true }),
  markAllRead: () => api.post<void>("/notifications/mark-all-read"),
}
