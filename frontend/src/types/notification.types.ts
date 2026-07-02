export type NotificationType = "info" | "success" | "warning" | "error"

export interface AppNotification {
  id: string
  type: NotificationType
  title: string
  message: string
  is_read: boolean
  created_at: string
}
