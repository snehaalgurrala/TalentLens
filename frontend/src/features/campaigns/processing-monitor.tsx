"use client"

import { AlertTriangle } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import type { CampaignProcessingStatus } from "@/types"

export interface ProcessingMonitorProps {
  status?: CampaignProcessingStatus
  isLoading: boolean
}

interface Stage {
  label: string
  count: number
  colorClass: string
}

function StageBar({ stage, total }: { stage: Stage; total: number }) {
  const percent = total > 0 ? Math.round((stage.count / total) * 100) : 0
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between text-caption">
        <span className="font-medium text-foreground">{stage.label}</span>
        <span className="text-muted-foreground">{stage.count}</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={cn("h-full rounded-full transition-all", stage.colorClass)}
          style={{ width: `${Math.min(100, Math.max(stage.count > 0 ? 4 : 0, percent))}%` }}
        />
      </div>
    </div>
  )
}

function ProcessingMonitor({ status, isLoading }: ProcessingMonitorProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Processing Monitor</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {isLoading || !status ? (
          <div className="flex flex-col gap-3">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-8 w-full" />
            ))}
          </div>
        ) : status.total_count === 0 ? (
          <p className="text-sm text-muted-foreground">
            No resumes uploaded yet — the pipeline will appear here once uploads begin.
          </p>
        ) : (
          <>
            <StageBar
              stage={{ label: "Uploaded / Queued", count: status.uploaded_count, colorClass: "bg-muted-foreground/40" }}
              total={status.total_count}
            />
            <StageBar
              stage={{ label: "Parsing", count: status.parsing_count, colorClass: "bg-warning" }}
              total={status.total_count}
            />
            <StageBar
              stage={{ label: "Embedding", count: status.embedding_count, colorClass: "bg-accent-purple" }}
              total={status.total_count}
            />
            <StageBar
              stage={{ label: "Ranking Ready", count: status.ready_for_ranking_count, colorClass: "bg-primary" }}
              total={status.total_count}
            />
            <StageBar
              stage={{ label: "Completed", count: status.completed_count, colorClass: "bg-success" }}
              total={status.total_count}
            />

            {status.failed_count > 0 && (
              <div className="flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-caption text-destructive-emphasis">
                <AlertTriangle className="size-4 shrink-0" aria-hidden="true" />
                {status.failed_count} file{status.failed_count === 1 ? "" : "s"} failed processing.
              </div>
            )}

            <p className="text-caption text-muted-foreground">
              Ranking is computed on demand from resumes that are parsed and embedded — there&apos;s
              no separate queued ranking step. Auto-refreshes every 15 seconds.
            </p>
          </>
        )}
      </CardContent>
    </Card>
  )
}

export { ProcessingMonitor }
