import type { Metadata } from "next"

import { StatusPage } from "@/layouts/status-page"

export const metadata: Metadata = { title: "Page not found" }

export default function NotFound() {
  return (
    <StatusPage
      code="404"
      title="Page not found"
      description="The page you're looking for doesn't exist or may have been moved."
    />
  )
}
