"use client"

import * as React from "react"

import { getAccessToken } from "@/lib/storage"
import { API_BASE_URL } from "@/services/axios"
import { notificationService } from "@/services/notification.service"
import { useNotificationStore } from "@/store/notification-store"
import type { AppNotification } from "@/types"

import { useAuth } from "./use-auth"

/**
 * Loads the current user's notification history once, then opens a single
 * Server-Sent-Events connection for live pushes — no polling. The backend
 * publishes to this stream the instant a notification is created (see
 * app.services.notification._publish), so a recruiter sees "Assessment
 * Completed" the moment it happens without refreshing.
 */
function useNotificationStream(): void {
  const { isAuthenticated } = useAuth()
  const { setNotifications, addNotification } = useNotificationStore()

  React.useEffect(() => {
    if (!isAuthenticated) return

    let cancelled = false
    notificationService
      .list()
      .then((notifications) => {
        if (!cancelled) setNotifications(notifications)
      })
      .catch(() => {
        // Best-effort: the live stream below still works even if this fails.
      })

    const token = getAccessToken()
    if (!token) return

    const source = new EventSource(
      `${API_BASE_URL}/notifications/stream?token=${encodeURIComponent(token)}`
    )
    source.onmessage = (event) => {
      try {
        addNotification(JSON.parse(event.data) as AppNotification)
      } catch {
        // Ignore a malformed event rather than tearing down the stream.
      }
    }

    return () => {
      cancelled = true
      source.close()
    }
  }, [isAuthenticated, setNotifications, addNotification])
}

export { useNotificationStream }
