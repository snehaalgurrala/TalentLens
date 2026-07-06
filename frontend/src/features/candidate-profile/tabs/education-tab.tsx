"use client"

import { Card, CardContent } from "@/components/ui/card"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { Grid } from "@/components/layout/grid"
import type { StructuredEducationEntry } from "@/types"

export interface EducationTabProps {
  education: StructuredEducationEntry[]
}

function EducationTab({ education }: EducationTabProps) {
  if (education.length === 0) {
    return (
      <TableEmptyState
        title="No education parsed"
        description="This resume didn't include a recognizable education section."
      />
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {education.map((entry, index) => (
        <Card key={index}>
          <CardContent>
            <Grid cols={2} colsSm={3} gap="md">
              <div className="flex flex-col gap-0.5">
                <span className="text-caption text-muted-foreground">Institution</span>
                <span className="text-sm text-foreground">{entry.institution ?? "—"}</span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-caption text-muted-foreground">Degree</span>
                <span className="text-sm text-foreground">{entry.degree ?? "—"}</span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-caption text-muted-foreground">Field</span>
                <span className="text-sm text-foreground">{entry.field ?? "—"}</span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-caption text-muted-foreground">Graduation Year</span>
                <span className="text-sm text-foreground">{entry.graduation_year ?? "—"}</span>
              </div>
            </Grid>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export { EducationTab }
