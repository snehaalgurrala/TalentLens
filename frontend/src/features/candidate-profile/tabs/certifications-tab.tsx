"use client"

import { Card, CardContent } from "@/components/ui/card"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { Grid } from "@/components/layout/grid"
import type { StructuredCertificationItem } from "@/types"

export interface CertificationsTabProps {
  certifications: StructuredCertificationItem[]
}

function CertificationsTab({ certifications }: CertificationsTabProps) {
  if (certifications.length === 0) {
    return (
      <TableEmptyState
        title="No certifications parsed"
        description="This resume didn't include a recognizable certifications section."
      />
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {certifications.map((cert, index) => (
        <Card key={index}>
          <CardContent>
            <Grid cols={2} colsSm={3} gap="md">
              <div className="flex flex-col gap-0.5">
                <span className="text-caption text-muted-foreground">Certification</span>
                <span className="text-sm text-foreground">{cert.name ?? "—"}</span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-caption text-muted-foreground">Issuer</span>
                <span className="text-sm text-foreground">{cert.issuer ?? "—"}</span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-caption text-muted-foreground">Issued Date</span>
                <span className="text-sm text-foreground">{cert.date ?? "—"}</span>
              </div>
            </Grid>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export { CertificationsTab }
