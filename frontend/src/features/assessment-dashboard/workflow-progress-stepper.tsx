"use client"

import { Check } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { PIPELINE_BOARD_COLUMNS } from "@/features/pipeline-board"
import { cn } from "@/lib/utils"
import type { PipelineStage } from "@/types"

// Only the automatic portion of the workflow (Applied -> Assessment
// Completed) — Interview/Hiring stages are out of scope for this sprint and
// are never automatically entered, so they're excluded here. Reuses the
// Pipeline Board's own column definitions rather than re-declaring the same
// stage list a second time.
const WORKFLOW_STEPS = PIPELINE_BOARD_COLUMNS.slice(0, 7)

export interface WorkflowProgressStepperProps {
  pipelineStage: PipelineStage | null
}

function stepIndexForStage(stage: PipelineStage | null): number {
  if (stage === null) return -1
  return WORKFLOW_STEPS.findIndex((step) => step.stages.includes(stage))
}

function WorkflowProgressStepper({ pipelineStage }: WorkflowProgressStepperProps) {
  const currentIndex = stepIndexForStage(pipelineStage)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Workflow Progress</CardTitle>
      </CardHeader>
      <CardContent>
        <ol
          className="flex flex-wrap items-center gap-x-1 gap-y-3"
          aria-label="Assessment workflow progress"
        >
          {WORKFLOW_STEPS.map((step, index) => {
            const isCurrent = index === currentIndex
            const isReached = currentIndex >= 0 && index <= currentIndex

            return (
              <li key={step.key} className="flex items-center gap-2">
                <div className="flex items-center gap-2">
                  <div
                    className={cn(
                      "flex size-7 shrink-0 items-center justify-center rounded-full border text-caption font-semibold",
                      isCurrent && "border-primary bg-primary text-primary-foreground",
                      isReached && !isCurrent && "border-success bg-success/10 text-success-emphasis",
                      !isReached && "border-border text-muted-foreground"
                    )}
                    aria-current={isCurrent ? "step" : undefined}
                  >
                    {isReached ? <Check className="size-4" aria-hidden="true" /> : index + 1}
                  </div>
                  <span
                    className={cn(
                      "text-sm whitespace-nowrap",
                      isReached ? "font-medium text-foreground" : "text-muted-foreground"
                    )}
                  >
                    {step.label}
                  </span>
                </div>
                {index < WORKFLOW_STEPS.length - 1 && (
                  <div
                    className={cn(
                      "h-px w-6 shrink-0",
                      index < currentIndex ? "bg-success" : "bg-border"
                    )}
                    aria-hidden="true"
                  />
                )}
              </li>
            )
          })}
        </ol>
      </CardContent>
    </Card>
  )
}

export { WorkflowProgressStepper }
