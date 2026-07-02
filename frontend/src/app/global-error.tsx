"use client"

import * as React from "react"

/** Catches errors thrown by the root layout itself — must render its own <html>/<body>. */
export default function GlobalError({
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
    <html lang="en">
      <body>
        <div className="flex min-h-dvh w-full flex-col items-center justify-center gap-3 px-4 text-center">
          <p className="text-sm font-semibold">500</p>
          <h1 className="text-2xl font-semibold">Something went wrong</h1>
          <p className="max-w-md text-sm text-neutral-500">
            A critical error occurred while loading the application.
          </p>
          <button
            type="button"
            onClick={reset}
            className="mt-2 rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium"
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  )
}
