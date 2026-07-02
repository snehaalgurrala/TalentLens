"use client"

import * as React from "react"
import { useIsFetching, useIsMutating } from "@tanstack/react-query"

import { cn } from "@/lib/utils"

interface LoadingContextValue {
  isLoading: boolean
  /** Increments the in-flight counter; call the returned function when the operation finishes. */
  startLoading: () => () => void
}

const LoadingContext = React.createContext<LoadingContextValue | null>(null)

function LoadingProvider({ children }: { children: React.ReactNode }) {
  const [count, setCount] = React.useState(0)

  // Every TanStack Query request/mutation drives the bar automatically —
  // `startLoading` is only needed for non-query async work (e.g. a raw fetch).
  const queryFetchCount = useIsFetching()
  const mutationCount = useIsMutating()

  const startLoading = React.useCallback(() => {
    setCount((c) => c + 1)
    let stopped = false
    return () => {
      if (stopped) return
      stopped = true
      setCount((c) => Math.max(0, c - 1))
    }
  }, [])

  const isLoading = count > 0 || queryFetchCount > 0 || mutationCount > 0

  const value = React.useMemo(() => ({ isLoading, startLoading }), [isLoading, startLoading])

  return (
    <LoadingContext.Provider value={value}>
      <div
        aria-hidden="true"
        className={cn(
          "fixed inset-x-0 top-0 z-(--z-toast) h-0.5 origin-left bg-primary transition-transform duration-300 ease-out",
          isLoading ? "scale-x-100 animate-pulse" : "scale-x-0"
        )}
      />
      {children}
    </LoadingContext.Provider>
  )
}

function useLoading(): LoadingContextValue {
  const ctx = React.useContext(LoadingContext)
  if (!ctx) {
    throw new Error("useLoading must be used within a LoadingProvider")
  }
  return ctx
}

export { LoadingProvider, useLoading }
