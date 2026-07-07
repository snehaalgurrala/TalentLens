export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

export function formatDuration(startedAt: string, completedAt: string | null): string {
  if (!completedAt) return "In progress"
  const seconds = Math.max(
    0,
    Math.round((new Date(completedAt).getTime() - new Date(startedAt).getTime()) / 1000)
  )
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  if (minutes === 0) return `${remainingSeconds}s`
  return `${minutes}m ${remainingSeconds}s`
}

export function scoreTone(score: number): string {
  if (score >= 85) return "text-success-emphasis"
  if (score >= 70) return "text-foreground"
  if (score >= 50) return "text-warning-emphasis"
  return "text-destructive-emphasis"
}
