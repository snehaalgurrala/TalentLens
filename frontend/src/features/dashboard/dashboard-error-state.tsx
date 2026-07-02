"use client"

import { AlertTriangle, RefreshCw, ShieldAlert, WifiOff, type LucideIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import type { ApiError } from "@/types"

export interface DashboardErrorStateProps {
  error: ApiError
  onRetry: () => void
}

function describeError(error: ApiError): { icon: LucideIcon; title: string; description: string } {
  if (error.status === 401 || error.status === 403) {
    return {
      icon: ShieldAlert,
      title: "You don't have access to this data",
      description: "Sign in with a recruiter account to view the dashboard.",
    }
  }
  if (error.status === 0) {
    return {
      icon: WifiOff,
      title: "Network error",
      description: "Check your connection and try again.",
    }
  }
  if (error.status >= 500) {
    return {
      icon: AlertTriangle,
      title: "Backend is offline",
      description: "The server is temporarily unavailable. Try again shortly.",
    }
  }
  return {
    icon: AlertTriangle,
    title: "Something went wrong",
    description: error.message || "Please try again.",
  }
}

function DashboardErrorState({ error, onRetry }: DashboardErrorStateProps) {
  const { icon: Icon, title, description } = describeError(error)

  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border px-4 py-12 text-center"
    >
      <span className="flex size-10 items-center justify-center rounded-full bg-destructive/10 text-destructive">
        <Icon className="size-5" aria-hidden="true" />
      </span>
      <div className="flex flex-col gap-1">
        <p className="text-body font-medium text-foreground">{title}</p>
        <p className="text-caption text-muted-foreground">{description}</p>
      </div>
      <Button variant="outline" size="sm" onClick={onRetry}>
        <RefreshCw className="size-4" aria-hidden="true" />
        Retry
      </Button>
    </div>
  )
}

export { DashboardErrorState }
