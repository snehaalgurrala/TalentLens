"use client"

import Link from "next/link"
import { ArrowRight } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { DashboardErrorState } from "@/features/dashboard"
import { useAssessmentSessionByCandidate } from "@/hooks"

export interface AssessmentTabProps {
  candidateId: string
  campaignId: string
}

function AssessmentTab({ candidateId, campaignId }: AssessmentTabProps) {
  const query = useAssessmentSessionByCandidate(candidateId, campaignId)

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

  return (
    <Card>
      <CardContent className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Badge variant={session.status === "COMPLETED" ? "success" : "pending"}>
            {session.status === "COMPLETED" ? "Completed" : "In Progress"}
          </Badge>
          <span className="text-sm text-muted-foreground">
            Started {new Date(session.started_at).toLocaleDateString()}
          </span>
        </div>
        <Button size="sm" asChild>
          <Link href={`/assessments/${session.id}`}>
            View Full Assessment
            <ArrowRight aria-hidden="true" />
          </Link>
        </Button>
      </CardContent>
    </Card>
  )
}

export { AssessmentTab }
