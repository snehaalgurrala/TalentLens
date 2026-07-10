"use client"

import { useRouter } from "next/navigation"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { cn } from "@/lib/utils"
import type { PerformerEntry } from "@/types"

export interface PerformersListProps {
  title: string
  description: string
  performers: PerformerEntry[]
  scoreTone: "success" | "destructive"
}

function PerformersList({ title, description, performers, scoreTone }: PerformersListProps) {
  const router = useRouter()

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {performers.length === 0 ? (
          <TableEmptyState
            title="No scored assessments yet"
            description="Performers appear once candidates complete assessments with a communication score."
          />
        ) : (
          <ul className="flex flex-col gap-3" role="list">
            {performers.map((performer) => (
              <li key={performer.session_id}>
                <button
                  type="button"
                  onClick={() => router.push(`/assessments/${performer.session_id}`)}
                  className="flex w-full items-center justify-between gap-3 rounded-lg border border-border px-3 py-2 text-left transition-colors hover:bg-muted/50"
                >
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-foreground">
                      {performer.candidate_name}
                    </span>
                    <span className="text-caption text-muted-foreground">
                      {performer.campaign_title}
                    </span>
                  </div>
                  <span
                    className={cn(
                      "text-h6 font-semibold tabular-nums",
                      scoreTone === "success" ? "text-success-emphasis" : "text-destructive-emphasis"
                    )}
                  >
                    {performer.overall_score}%
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

export { PerformersList }
