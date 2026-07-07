"use client"

import { CheckCircle2 } from "lucide-react"

import { Container } from "@/components/layout/container"
import { cn } from "@/lib/utils"

export type AssessmentSectionKey = "aptitude" | "read-aloud" | "listen-repeat"

const SECTIONS: { key: AssessmentSectionKey; label: string }[] = [
  { key: "aptitude", label: "Aptitude" },
  { key: "read-aloud", label: "Read Aloud" },
  { key: "listen-repeat", label: "Listen & Repeat" },
]

export interface AssessmentProgressHeaderProps {
  current: AssessmentSectionKey
  completed: Record<AssessmentSectionKey, boolean>
}

function AssessmentProgressHeader({ current, completed }: AssessmentProgressHeaderProps) {
  return (
    <div className="sticky top-0 z-sticky border-b border-border bg-background/95 backdrop-blur">
      <Container size="md" className="flex flex-col gap-2 py-4">
        <div className="flex items-center gap-4 sm:gap-6">
          {SECTIONS.map((section, index) => {
            const isComplete = completed[section.key]
            const isCurrent = section.key === current
            return (
              <div key={section.key} className="flex flex-1 flex-col gap-1.5">
                <div className="flex items-center gap-1.5 text-caption font-medium">
                  {isComplete ? (
                    <CheckCircle2 className="size-3.5 text-success" aria-hidden="true" />
                  ) : (
                    <span
                      className={cn(
                        "flex size-3.5 items-center justify-center rounded-full text-[0.65rem] leading-none",
                        isCurrent
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-muted-foreground"
                      )}
                    >
                      {index + 1}
                    </span>
                  )}
                  <span
                    className={cn(
                      isComplete || isCurrent ? "text-foreground" : "text-muted-foreground"
                    )}
                  >
                    {section.label}
                  </span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all",
                      isComplete ? "w-full bg-success" : isCurrent ? "w-1/2 bg-primary" : "w-0"
                    )}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </Container>
    </div>
  )
}

export { AssessmentProgressHeader }
