import type { Metadata } from "next"

import { StatusPage } from "@/layouts/status-page"

export const metadata: Metadata = { title: "You're offline" }

export default function OfflinePage() {
  return (
    <StatusPage
      title="You're offline"
      description="Check your internet connection and try again."
      actionLabel="Retry"
      actionHref="/dashboard"
    />
  )
}
