import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"

function scoreTone(score: number): string {
  if (score >= 85) return "text-success-emphasis"
  if (score >= 70) return "text-foreground"
  if (score >= 50) return "text-warning-emphasis"
  return "text-destructive-emphasis"
}

function CandidateScoreCell({ score }: { score: number | null }) {
  if (score === null) {
    return <span className="text-muted-foreground">—</span>
  }
  return (
    <div className="flex w-24 flex-col gap-1">
      <span className={cn("text-sm font-semibold tabular-nums", scoreTone(score))}>{score}%</span>
      <Progress value={score} className="h-1" />
    </div>
  )
}

export { CandidateScoreCell }
