"use client"

import * as React from "react"
import Link from "next/link"

import { Button } from "@/components/ui/button"

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  React.useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div className="flex min-h-dvh w-full flex-col items-center justify-center gap-3 bg-background px-4 text-center">
      <p className="text-sm font-semibold text-primary">500</p>
      <h1 className="text-h2 text-foreground">Something went wrong</h1>
      <p className="max-w-md text-body text-muted-foreground">
        An unexpected error occurred. Try again, or head back to the dashboard.
      </p>
      <div className="mt-2 flex items-center gap-2">
        <Button variant="outline" onClick={reset}>
          Try again
        </Button>
        <Button asChild>
          <Link href="/dashboard">Back to dashboard</Link>
        </Button>
      </div>
    </div>
  )
}
