"use client"

import * as React from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { DataTable, type DataTableColumn } from "@/components/ui/data-table"
import { Row, Section } from "../_components/section"

interface CandidateRow {
  id: string
  name: string
  role: string
  status: "active" | "pending" | "rejected"
  score: number
}

const rows: CandidateRow[] = [
  { id: "1", name: "Amara Okafor", role: "Product Designer", status: "active", score: 92 },
  { id: "2", name: "Liam Chen", role: "Backend Engineer", status: "pending", score: 78 },
  { id: "3", name: "Sofia Rossi", role: "Data Analyst", status: "rejected", score: 41 },
]

const columns: DataTableColumn<CandidateRow>[] = [
  { key: "name", header: "Name", sortable: true, render: (row) => row.name },
  { key: "role", header: "Role", render: (row) => row.role },
  {
    key: "status",
    header: "Status",
    render: (row) => <Badge variant={row.status}>{row.status}</Badge>,
  },
  {
    key: "score",
    header: "Match",
    sortable: true,
    align: "right",
    render: (row) => `${row.score}%`,
  },
]

function DataTableSection() {
  const [state, setState] = React.useState<"ready" | "loading" | "empty">(
    "ready"
  )
  const [sortKey, setSortKey] = React.useState<string>()
  const [sortDirection, setSortDirection] = React.useState<"asc" | "desc">(
    "asc"
  )

  return (
    <Section
      id="data-table"
      title="Tables"
      description="DataTable wraps the base Table with sorting-ready column headers and dedicated loading/empty states."
    >
      <Row label="State">
        <Button
          size="sm"
          variant={state === "ready" ? "secondary" : "outline"}
          onClick={() => setState("ready")}
        >
          Ready
        </Button>
        <Button
          size="sm"
          variant={state === "loading" ? "secondary" : "outline"}
          onClick={() => setState("loading")}
        >
          Loading
        </Button>
        <Button
          size="sm"
          variant={state === "empty" ? "secondary" : "outline"}
          onClick={() => setState("empty")}
        >
          Empty
        </Button>
      </Row>

      <div className="rounded-lg border border-border">
        <DataTable
          columns={columns}
          data={rows}
          getRowKey={(row) => row.id}
          state={state}
          sortKey={sortKey}
          sortDirection={sortDirection}
          onSortChange={(key) => {
            if (key === sortKey) {
              setSortDirection((d) => (d === "asc" ? "desc" : "asc"))
            } else {
              setSortKey(key)
              setSortDirection("asc")
            }
          }}
          emptyTitle="No candidates yet"
          emptyDescription="Invite candidates to see them ranked here."
        />
      </div>
    </Section>
  )
}

export { DataTableSection }
