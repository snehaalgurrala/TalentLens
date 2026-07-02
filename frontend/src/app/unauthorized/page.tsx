import type { Metadata } from "next"

import { StatusPage } from "@/layouts/status-page"

export const metadata: Metadata = { title: "Unauthorized" }

export default function UnauthorizedPage() {
  return (
    <StatusPage
      code="401"
      title="Unauthorized"
      description="You need to be logged in to view this page."
      actionLabel="Log in"
      actionHref="/login"
    />
  )
}
