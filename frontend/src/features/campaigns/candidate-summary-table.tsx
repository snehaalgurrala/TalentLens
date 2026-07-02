"use client"

import * as React from "react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { DataTable, type DataTableColumn } from "@/components/ui/data-table"
import { DashboardErrorState } from "@/features/dashboard"
import { useCampaignRankings } from "@/hooks"
import type { ApiError, CandidateRanking, ReviewStatus } from "@/types"

import { CandidateDetailDialog } from "./candidate-detail-dialog"

export interface CandidateSummaryTableProps {
  campaignId: string
}

const TOP_N = 10

const REVIEW_STATUS_VARIANT: Record<ReviewStatus, React.ComponentProps<typeof Badge>["variant"]> = {
  PENDING: "secondary",
  SHORTLISTED: "shortlisted",
  REJECTED: "rejected",
}

function CandidateSummaryTable({ campaignId }: CandidateSummaryTableProps) {
  const [selected, setSelected] = React.useState<CandidateRanking | null>(null)
  const rankingsQuery = useCampaignRankings(campaignId)
  const rankings = (rankingsQuery.data ?? []).slice(0, TOP_N)
  const notReadyError = (rankingsQuery.error as ApiError | undefined)?.status === 422

  const columns: DataTableColumn<CandidateRanking>[] = [
    { key: "rank", header: "Rank", align: "center", render: (r) => r.rank },
    { key: "candidate", header: "Candidate", render: (r) => <span className="font-medium text-foreground">{r.candidate_name}</span> },
    { key: "company", header: "Company", render: (r) => r.current_company || <span className="text-muted-foreground">—</span> },
    {
      key: "experience",
      header: "Experience",
      render: (r) => (r.years_of_experience !== null ? `${r.years_of_experience} yrs` : <span className="text-muted-foreground">—</span>),
    },
    { key: "score", header: "Match Score", align: "right", render: (r) => `${r.overall_score}%` },
    {
      key: "status",
      header: "Status",
      render: (r) => <Badge variant={REVIEW_STATUS_VARIANT[r.review_status]}>{r.review_status}</Badge>,
    },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>Top Candidates</CardTitle>
      </CardHeader>
      <CardContent>
        {rankingsQuery.isError && !notReadyError ? (
          <DashboardErrorState error={rankingsQuery.error} onRetry={() => rankingsQuery.refetch()} />
        ) : (
          <DataTable
            columns={columns}
            data={rankings}
            getRowKey={(r) => r.resume_file_id}
            state={rankingsQuery.isPending ? "loading" : "ready"}
            emptyTitle={notReadyError ? "Not ready to rank yet" : "No candidates yet"}
            emptyDescription={
              notReadyError
                ? "Add a job description and wait for it to finish parsing to see ranked candidates."
                : "Upload resumes to start ranking candidates."
            }
            onRowClick={setSelected}
          />
        )}
      </CardContent>
      <CandidateDetailDialog candidate={selected} onOpenChange={(open) => !open && setSelected(null)} />
    </Card>
  )
}

export { CandidateSummaryTable }
