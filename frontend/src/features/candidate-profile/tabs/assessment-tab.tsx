"use client"

import Link from "next/link"
import { ArrowRight } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { DashboardErrorState } from "@/features/dashboard"
import { useAssessmentSessionByCandidate, useAssessmentSessionFull } from "@/hooks"

export interface AssessmentTabProps {
  candidateId: string
  campaignId: string
}

function AssessmentTab({ candidateId, campaignId }: AssessmentTabProps) {
  const query = useAssessmentSessionByCandidate(candidateId, campaignId)
  const fullQuery = useAssessmentSessionFull(query.data?.id)

  if (query.isPending) {
    return <Skeleton className="h-32 w-full" />
  }

  if (query.isError) {
    if (query.error.status === 404) {
      return (
        <TableEmptyState
          title="Assessment not started for this candidate yet"
          description="Once this candidate begins their communication assessment, results will appear here."
        />
      )
    }
    return <DashboardErrorState error={query.error} onRetry={() => query.refetch()} />
  }

  const session = query.data
  const overallScore = fullQuery.data?.communication_assessment?.overall_score ?? null

  return (
    <Card>
      <CardContent className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant={session.status === "COMPLETED" ? "success" : "pending"}>
            {session.status === "COMPLETED" ? "Completed" : "In Progress"}
          </Badge>
          <span className="text-sm text-muted-foreground">
            {session.status === "COMPLETED" && session.completed_at
              ? `Completed ${new Date(session.completed_at).toLocaleDateString()}`
              : `Started ${new Date(session.started_at).toLocaleDateString()}`}
          </span>
          <span className="text-sm text-muted-foreground">
            Overall Communication Score:{" "}
            <span className="font-medium text-foreground">
              {overallScore === null ? "Pending" : `${overallScore}%`}
            </span>
          </span>
        </div>
        <Button size="sm" asChild>
          <Link href={`/assessments/${session.id}`}>
            View Dashboard
            <ArrowRight aria-hidden="true" />
          </Link>
        </Button>
      </CardContent>
    </Card>
  )
}

export { AssessmentTab }
