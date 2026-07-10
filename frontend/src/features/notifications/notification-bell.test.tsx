import * as React from "react"

import { render, screen } from "@testing-library/react"

import { NotificationStoreProvider, useNotificationStore } from "@/store/notification-store"
import type { AppNotification } from "@/types"

import { NotificationBell } from "./notification-bell"

// Real interaction with the dropdown's popover content (mark-read,
// mark-all-read) is exercised manually rather than here — this codebase has
// no existing precedent for opening a Radix DropdownMenu in jsdom, and the
// trigger button's own onClick doesn't reliably flip Radix's open state
// under fireEvent in this environment. These tests cover what matters for a
// component that's now mounted on every authenticated page: it must render
// safely and reflect unread state correctly.
jest.mock("@/hooks/use-notification-stream", () => ({
  useNotificationStream: jest.fn(),
}))

jest.mock("@/services/notification.service", () => ({
  notificationService: {
    markRead: jest.fn().mockResolvedValue(undefined),
    markAllRead: jest.fn().mockResolvedValue(undefined),
  },
}))

function makeNotification(overrides: Partial<AppNotification> = {}): AppNotification {
  return {
    id: "notif-1",
    type: "success",
    title: "Assessment Completed",
    message: "Jane Doe completed their assessment.",
    is_read: false,
    created_at: new Date().toISOString(),
    ...overrides,
  }
}

function Seed({ notifications }: { notifications: AppNotification[] }) {
  const { setNotifications } = useNotificationStore()
  React.useEffect(() => {
    setNotifications(notifications)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  return null
}

function renderBell(notifications: AppNotification[] = []) {
  return render(
    <NotificationStoreProvider>
      <Seed notifications={notifications} />
      <NotificationBell />
    </NotificationStoreProvider>
  )
}

describe("NotificationBell", () => {
  afterEach(() => jest.clearAllMocks())

  it("renders without crashing and shows no unread badge when empty", () => {
    renderBell([])
    expect(screen.getByLabelText("Notifications")).toBeInTheDocument()
  })

  it("shows the unread count badge", () => {
    renderBell([makeNotification({ is_read: false })])
    expect(screen.getByLabelText(/1 unread/i)).toBeInTheDocument()
  })

  it("does not show an unread badge once everything is read", () => {
    renderBell([makeNotification({ is_read: true })])
    expect(screen.getByLabelText("Notifications")).toBeInTheDocument()
    expect(screen.queryByLabelText(/unread/i)).not.toBeInTheDocument()
  })

  it("caps the displayed unread count at 9+", () => {
    renderBell(Array.from({ length: 12 }, (_, i) => makeNotification({ id: `n${i}` })))
    expect(screen.getByLabelText(/12 unread/i)).toBeInTheDocument()
    expect(screen.getByText("9+")).toBeInTheDocument()
  })
})
