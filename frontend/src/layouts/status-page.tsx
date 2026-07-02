import * as React from "react"
import Link from "next/link"

import { Button } from "@/components/ui/button"

export interface StatusPageProps {
  code?: string
  title: string
  description: string
  actionLabel?: string
  actionHref?: string
}

/** Shared shell for full-page status states — 404, 500, offline, unauthorized, forbidden. */
function StatusPage({
  code,
  title,
  description,
  actionLabel = "Back to dashboard",
  actionHref = "/dashboard",
}: StatusPageProps) {
  return (
    <div className="flex min-h-dvh w-full flex-col items-center justify-center gap-3 bg-background px-4 text-center">
      {code && <p className="text-sm font-semibold text-primary">{code}</p>}
      <h1 className="text-h2 text-foreground">{title}</h1>
      <p className="max-w-md text-body text-muted-foreground">{description}</p>
      {actionHref && (
        <Button asChild className="mt-2">
          <Link href={actionHref}>{actionLabel}</Link>
        </Button>
      )}
    </div>
  )
}

export { StatusPage }
