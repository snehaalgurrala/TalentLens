"use client"

import * as React from "react"
import { Clock } from "lucide-react"

import { cn } from "@/lib/utils"

export interface TimerProps {
  deadlineAt: number
  className?: string
}

function formatRemaining(ms: number): string {
  const totalSeconds = Math.max(0, Math.ceil(ms / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, "0")}`
}

/** Client-side visual countdown only — not tied to a server deadline. */
function Timer({ deadlineAt, className }: TimerProps) {
  const [remainingMs, setRemainingMs] = React.useState(() => deadlineAt - Date.now())

  React.useEffect(() => {
    const interval = setInterval(() => {
      setRemainingMs(deadlineAt - Date.now())
    }, 1000)
    return () => clearInterval(interval)
  }, [deadlineAt])

  const isLow = remainingMs < 60_000

  return (
    <div
      className={cn(
        "flex items-center gap-1.5 text-caption font-medium tabular-nums",
        isLow ? "text-destructive-emphasis" : "text-muted-foreground",
        className
      )}
      role="timer"
      aria-live="polite"
      aria-atomic="true"
    >
      <Clock className="size-3.5" aria-hidden="true" />
      {formatRemaining(remainingMs)}
    </div>
  )
}

export { Timer }
