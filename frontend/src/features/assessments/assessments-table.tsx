"use client"

import { Badge } from "@/components/ui/badge"
import { DataTable, type DataTableColumn } from "@/components/ui/data-table"
import { Progress } from "@/components/ui/progress"
import { CandidateScoreCell } from "@/features/candidates"
import { formatDate } from "@/utils"
import type { AssessmentSessionListItem } from "@/types"

export interface AssessmentsTableProps {
  sessions: AssessmentSessionListItem[]
  isLoading: boolean
  onRowClick: (session: AssessmentSessionListItem) => void
}

const SECTION_LABELS: Record<AssessmentSessionListItem["current_section"], string> = {
  APTITUDE: "Aptitude",
  READ_ALOUD: "Read Aloud",
  LISTEN_REPEAT: "Listen & Repeat",
}

function ProgressCell({ session }: { session: AssessmentSessionListItem }) {
  if (session.status === "COMPLETED") {
    return <span className="text-caption font-medium text-success-emphasis">Completed</span>
  }
  return (
    <div className="flex w-32 flex-col gap-1">
      <span className="text-caption text-muted-foreground">
        {SECTION_LABELS[session.current_section]}
      </span>
      <Progress value={session.progress_percent} className="h-1" />
    </div>
  )
}

function AssessmentsTable({ sessions, isLoading, onRowClick }: AssessmentsTableProps) {
  const columns: DataTableColumn<AssessmentSessionListItem>[] = [
    {
      key: "candidate",
      header: "Candidate",
      render: (session) => (
        <div className="flex flex-col">
          <span className="font-medium text-foreground">
            {session.candidate.first_name} {session.candidate.last_name}
          </span>
          {session.candidate.email && (
            <span className="text-caption text-muted-foreground">{session.candidate.email}</span>
          )}
        </div>
      ),
    },
    {
      key: "campaign",
      header: "Campaign",
      render: (session) => session.campaign.title,
    },
    {
      key: "status",
      header: "Status",
      render: (session) => (
        <Badge variant={session.status === "COMPLETED" ? "success" : "pending"}>
          {session.status === "COMPLETED" ? "Completed" : "In Progress"}
        </Badge>
      ),
    },
    {
      key: "started_at",
      header: "Date",
      render: (session) => formatDate(session.started_at),
    },
    {
      key: "overall_score",
      header: "Overall Communication Score",
      render: (session) => <CandidateScoreCell score={session.overall_score} />,
    },
    {
      key: "progress",
      header: "Assessment Progress",
      render: (session) => <ProgressCell session={session} />,
    },
  ]

  return (
    <DataTable
      columns={columns}
      data={sessions}
      getRowKey={(session) => session.session_id}
      state={isLoading ? "loading" : sessions.length === 0 ? "empty" : "ready"}
      emptyTitle="No assessments yet"
      emptyDescription="Send an assessment invitation from a candidate's profile to get started."
      onRowClick={onRowClick}
    />
  )
}

export { AssessmentsTable }
