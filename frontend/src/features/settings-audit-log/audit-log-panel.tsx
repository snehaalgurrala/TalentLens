"use client"

import * as React from "react"

import { Stack } from "@/components/layout/stack"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { TableLoadingState } from "@/components/ui/table-loading-state"
import { DashboardErrorState } from "@/features/dashboard"
import { useAuditLog } from "@/hooks"
import type { AuditLogEntry, AuditLogFilters } from "@/types"

const PAGE_SIZE = 20

function toIsoDate(value: string): string | undefined {
  return value ? new Date(value).toISOString() : undefined
}

function truncateId(value: string | null, length = 8) {
  if (!value) return "—"
  return value.length > length ? `${value.slice(0, length)}…` : value
}

function AuditLogPanel() {
  const [actionInput, setActionInput] = React.useState("")
  const [entityTypeInput, setEntityTypeInput] = React.useState("")
  const [dateFromInput, setDateFromInput] = React.useState("")
  const [dateToInput, setDateToInput] = React.useState("")
  const [filters, setFilters] = React.useState<AuditLogFilters>({ limit: PAGE_SIZE, offset: 0 })
  const [selectedEntry, setSelectedEntry] = React.useState<AuditLogEntry | null>(null)

  const auditLogQuery = useAuditLog(filters)

  function handleApplyFilters(event: React.FormEvent) {
    event.preventDefault()
    setFilters({
      action: actionInput || undefined,
      entity_type: entityTypeInput || undefined,
      date_from: toIsoDate(dateFromInput),
      date_to: toIsoDate(dateToInput),
      limit: PAGE_SIZE,
      offset: 0,
    })
  }

  function handleReset() {
    setActionInput("")
    setEntityTypeInput("")
    setDateFromInput("")
    setDateToInput("")
    setFilters({ limit: PAGE_SIZE, offset: 0 })
  }

  const offset = filters.offset ?? 0
  const total = auditLogQuery.data?.total ?? 0
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  function goToPage(page: number) {
    const clamped = Math.min(Math.max(page, 1), totalPages)
    setFilters((prev) => ({ ...prev, offset: (clamped - 1) * PAGE_SIZE }))
  }

  return (
    <Stack gap="lg">
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleApplyFilters} className="flex flex-wrap items-end gap-3">
            <Stack gap="xs">
              <Label htmlFor="audit-action">Action</Label>
              <Input
                id="audit-action"
                placeholder="e.g. login"
                value={actionInput}
                onChange={(event) => setActionInput(event.target.value)}
                className="w-40"
              />
            </Stack>
            <Stack gap="xs">
              <Label htmlFor="audit-entity-type">Entity Type</Label>
              <Input
                id="audit-entity-type"
                placeholder="e.g. candidate"
                value={entityTypeInput}
                onChange={(event) => setEntityTypeInput(event.target.value)}
                className="w-40"
              />
            </Stack>
            <Stack gap="xs">
              <Label htmlFor="audit-date-from">From</Label>
              <Input
                id="audit-date-from"
                type="date"
                value={dateFromInput}
                onChange={(event) => setDateFromInput(event.target.value)}
                className="w-40"
              />
            </Stack>
            <Stack gap="xs">
              <Label htmlFor="audit-date-to">To</Label>
              <Input
                id="audit-date-to"
                type="date"
                value={dateToInput}
                onChange={(event) => setDateToInput(event.target.value)}
                className="w-40"
              />
            </Stack>
            <div className="flex gap-2">
              <Button type="submit" size="sm">
                Apply
              </Button>
              <Button type="button" variant="outline" size="sm" onClick={handleReset}>
                Reset
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {auditLogQuery.isError ? (
        <DashboardErrorState error={auditLogQuery.error} onRetry={() => auditLogQuery.refetch()} />
      ) : (
        <Card>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Entity</TableHead>
                  <TableHead>Result</TableHead>
                  <TableHead className="text-right">Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {auditLogQuery.isPending ? (
                  <TableLoadingState columns={6} />
                ) : auditLogQuery.data.items.length === 0 ? (
                  <TableRow className="hover:bg-transparent">
                    <TableCell colSpan={6}>
                      <TableEmptyState
                        title="No audit log entries"
                        description="No events match the current filters."
                      />
                    </TableCell>
                  </TableRow>
                ) : (
                  auditLogQuery.data.items.map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell>{new Date(entry.created_at).toLocaleString()}</TableCell>
                      <TableCell>{entry.actor_name ?? truncateId(entry.actor_id)}</TableCell>
                      <TableCell>{entry.action}</TableCell>
                      <TableCell>
                        {entry.entity_type}
                        {entry.entity_id && (
                          <span className="text-muted-foreground"> · {truncateId(entry.entity_id)}</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant={entry.result === "success" ? "active" : "rejected"}>
                          {entry.result}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="outline" size="sm" onClick={() => setSelectedEntry(entry)}>
                          View Details
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {!auditLogQuery.isPending && !auditLogQuery.isError && total > 0 && (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                href="#"
                onClick={(event) => {
                  event.preventDefault()
                  goToPage(currentPage - 1)
                }}
                className={currentPage <= 1 ? "pointer-events-none opacity-50" : undefined}
              />
            </PaginationItem>
            <PaginationItem>
              <span className="px-2 text-caption text-muted-foreground">
                Page {currentPage} of {totalPages} · {total} entries
              </span>
            </PaginationItem>
            <PaginationItem>
              <PaginationNext
                href="#"
                onClick={(event) => {
                  event.preventDefault()
                  goToPage(currentPage + 1)
                }}
                className={currentPage >= totalPages ? "pointer-events-none opacity-50" : undefined}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}

      <Dialog open={selectedEntry !== null} onOpenChange={(open) => !open && setSelectedEntry(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Event Metadata</DialogTitle>
          </DialogHeader>
          <pre className="max-h-96 overflow-auto rounded-lg bg-muted p-3 text-xs">
            {JSON.stringify(selectedEntry?.event_metadata ?? null, null, 2)}
          </pre>
        </DialogContent>
      </Dialog>
    </Stack>
  )
}

export { AuditLogPanel }
