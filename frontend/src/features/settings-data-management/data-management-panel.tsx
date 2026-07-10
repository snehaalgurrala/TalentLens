"use client"

import { toast } from "sonner"

import { Grid } from "@/components/layout/grid"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useExportAssessments, useExportAuditLog, useExportCandidates } from "@/hooks"

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Something went wrong"
}

async function runExport(exportFn: () => Promise<void>) {
  try {
    await exportFn()
  } catch (error) {
    toast.error(getErrorMessage(error))
  }
}

function ExportCard({
  title,
  description,
  onExport,
  isPending,
}: {
  title: string
  description: string
  onExport: () => void
  isPending: boolean
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <Button variant="outline" size="sm" onClick={onExport} isLoading={isPending}>
          Download CSV
        </Button>
      </CardContent>
    </Card>
  )
}

function DataManagementPanel() {
  const exportCandidates = useExportCandidates()
  const exportAssessments = useExportAssessments()
  const exportAuditLog = useExportAuditLog()

  return (
    <Grid cols={1} colsSm={2} colsLg={3} gap="md">
      <ExportCard
        title="Candidates"
        description="Export all candidate records for this organization as CSV."
        onExport={() => runExport(() => exportCandidates.mutateAsync())}
        isPending={exportCandidates.isPending}
      />
      <ExportCard
        title="Assessments"
        description="Export all assessment session records as CSV."
        onExport={() => runExport(() => exportAssessments.mutateAsync())}
        isPending={exportAssessments.isPending}
      />
      <ExportCard
        title="Audit Log"
        description="Export the full audit log as CSV."
        onExport={() => runExport(() => exportAuditLog.mutateAsync())}
        isPending={exportAuditLog.isPending}
      />

      <Card>
        <CardHeader>
          <CardTitle>Retention Policy</CardTitle>
          <CardDescription>Current data retention configuration.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Default retention: 365 days (display only — no automated deletion job exists yet).
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Backup Status</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm font-medium text-foreground">Not configured</p>
          <p className="text-caption text-muted-foreground">
            Automated backups are not yet configured for this environment.
          </p>
        </CardContent>
      </Card>
    </Grid>
  )
}

export { DataManagementPanel }
