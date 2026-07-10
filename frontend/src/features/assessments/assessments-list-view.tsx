"use client"

import { useRouter } from "next/navigation"

import { Stack } from "@/components/layout/stack"
import { DashboardErrorState } from "@/features/dashboard"
import { useAssessmentSessionsList } from "@/hooks"

import { AssessmentsTable } from "./assessments-table"

function AssessmentsListView() {
  const router = useRouter()
  const sessionsQuery = useAssessmentSessionsList()
  const sessions = sessionsQuery.data?.items ?? []

  return (
    <Stack gap="lg">
      {sessionsQuery.isError ? (
        <DashboardErrorState error={sessionsQuery.error} onRetry={() => sessionsQuery.refetch()} />
      ) : (
        <AssessmentsTable
          sessions={sessions}
          isLoading={sessionsQuery.isPending}
          onRowClick={(session) => router.push(`/assessments/${session.session_id}`)}
        />
      )}
    </Stack>
  )
}

export { AssessmentsListView }
