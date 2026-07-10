"use client"

import { Bell, CheckCheck } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { useNotificationStream } from "@/hooks/use-notification-stream"
import { notificationService } from "@/services/notification.service"
import { useNotificationStore } from "@/store/notification-store"
import type { AppNotification } from "@/types"

function formatRelativeTime(isoDate: string): string {
  const diffMs = Date.now() - new Date(isoDate).getTime()
  const minutes = Math.round(diffMs / 60_000)
  if (minutes < 1) return "just now"
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.round(hours / 24)}d ago`
}

function NotificationBell() {
  useNotificationStream()
  const { notifications, unreadCount, markRead, markAllRead } = useNotificationStore()

  function handleSelect(notification: AppNotification) {
    if (notification.is_read) return
    markRead(notification.id)
    notificationService.markRead(notification.id).catch(() => {
      // Best-effort — the next full list() refetch will reconcile.
    })
  }

  function handleMarkAllRead() {
    markAllRead()
    notificationService.markAllRead().catch(() => {})
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="relative flex size-9 items-center justify-center rounded-full outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50"
        aria-label={unreadCount > 0 ? `Notifications (${unreadCount} unread)` : "Notifications"}
      >
        <Bell className="size-4.5" aria-hidden="true" />
        {unreadCount > 0 && (
          <Badge
            variant="destructive"
            className="absolute -top-0.5 -right-0.5 h-4.5 min-w-4.5 justify-center rounded-full px-1 text-[10px]"
          >
            {unreadCount > 9 ? "9+" : unreadCount}
          </Badge>
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel className="flex items-center justify-between gap-2">
          <span>Notifications</span>
          {unreadCount > 0 && (
            <Button variant="ghost" size="sm" className="h-auto gap-1 px-1.5 py-1" onClick={handleMarkAllRead}>
              <CheckCheck className="size-3.5" aria-hidden="true" />
              Mark all read
            </Button>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {notifications.length === 0 ? (
          <TableEmptyState title="No notifications yet" />
        ) : (
          <div className="flex max-h-96 flex-col overflow-y-auto">
            {notifications.map((notification) => (
              <DropdownMenuItem
                key={notification.id}
                className="flex flex-col items-start gap-0.5 whitespace-normal"
                onSelect={() => handleSelect(notification)}
              >
                <div className="flex w-full items-center gap-1.5">
                  {!notification.is_read && (
                    <span className="size-1.5 shrink-0 rounded-full bg-primary" aria-hidden="true" />
                  )}
                  <span className="truncate text-sm font-medium text-foreground">
                    {notification.title}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground">{notification.message}</span>
                <span className="text-caption text-muted-foreground">
                  {formatRelativeTime(notification.created_at)}
                </span>
              </DropdownMenuItem>
            ))}
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export { NotificationBell }
