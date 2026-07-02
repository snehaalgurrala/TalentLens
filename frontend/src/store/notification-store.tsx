"use client"

import * as React from "react"

import type { AppNotification } from "@/types"

interface NotificationStoreValue {
  notifications: AppNotification[]
  unreadCount: number
  setNotifications: (notifications: AppNotification[]) => void
  addNotification: (notification: AppNotification) => void
  markRead: (id: string) => void
  markAllRead: () => void
}

const NotificationStoreContext = React.createContext<NotificationStoreValue | null>(null)

function NotificationStoreProvider({ children }: { children: React.ReactNode }) {
  const [notifications, setNotifications] = React.useState<AppNotification[]>([])

  const addNotification = React.useCallback((notification: AppNotification) => {
    setNotifications((prev) => [notification, ...prev])
  }, [])

  const markRead = React.useCallback((id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
    )
  }, [])

  const markAllRead = React.useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
  }, [])

  const unreadCount = React.useMemo(
    () => notifications.filter((n) => !n.is_read).length,
    [notifications]
  )

  const value = React.useMemo(
    () => ({ notifications, unreadCount, setNotifications, addNotification, markRead, markAllRead }),
    [notifications, unreadCount, addNotification, markRead, markAllRead]
  )

  return (
    <NotificationStoreContext.Provider value={value}>
      {children}
    </NotificationStoreContext.Provider>
  )
}

function useNotificationStore(): NotificationStoreValue {
  const ctx = React.useContext(NotificationStoreContext)
  if (!ctx) {
    throw new Error("useNotificationStore must be used within a NotificationStoreProvider")
  }
  return ctx
}

export { NotificationStoreProvider, useNotificationStore }
