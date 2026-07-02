import type { Metadata } from "next"

import { StatusPage } from "@/layouts/status-page"

export const metadata: Metadata = { title: "Forbidden" }

export default function ForbiddenPage() {
  return (
    <StatusPage
      code="403"
      title="Forbidden"
      description="You don't have permission to access this page."
      actionLabel="Back to dashboard"
      actionHref="/dashboard"
    />
  )
}
