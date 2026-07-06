"use client"

import { Card, CardContent } from "@/components/ui/card"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import type { StructuredExperienceItem } from "@/types"

export interface ExperienceTabProps {
  experience: StructuredExperienceItem[]
}

function ExperienceTab({ experience }: ExperienceTabProps) {
  if (experience.length === 0) {
    return (
      <TableEmptyState
        title="No experience parsed"
        description="This resume didn't include a recognizable work-experience section."
      />
    )
  }

  return (
    <ol className="flex flex-col gap-4" aria-label="Work experience timeline">
      {experience.map((entry, index) => (
        <li key={index}>
          <Card>
            <CardContent className="flex flex-col gap-1.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-body font-medium text-foreground">{entry.role ?? "Role"}</span>
                <span className="text-caption text-muted-foreground">
                  {entry.start_date ?? "?"} – {entry.end_date ?? "Present"}
                </span>
              </div>
              <span className="text-sm text-muted-foreground">{entry.company ?? "Company unknown"}</span>
              {entry.description && (
                <p className="text-sm text-foreground whitespace-pre-line">{entry.description}</p>
              )}
            </CardContent>
          </Card>
        </li>
      ))}
    </ol>
  )
}

export { ExperienceTab }
