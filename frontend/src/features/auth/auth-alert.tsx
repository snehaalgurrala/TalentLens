import * as React from "react"
import { AlertCircle, Info } from "lucide-react"

import { cn } from "@/lib/utils"

interface AuthAlertProps {
  variant?: "error" | "info"
  children: React.ReactNode
  className?: string
}

/** Small inline alert for form-level API errors / informational notices on auth pages. */
function AuthAlert({ variant = "error", children, className }: AuthAlertProps) {
  const Icon = variant === "error" ? AlertCircle : Info

  return (
    <div
      role="alert"
      className={cn(
        "flex items-start gap-2 rounded-lg border px-3 py-2 text-sm",
        variant === "error"
          ? "border-destructive/30 bg-destructive/10 text-destructive"
          : "border-border bg-muted text-muted-foreground",
        className
      )}
    >
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <span>{children}</span>
    </div>
  )
}

export { AuthAlert }
