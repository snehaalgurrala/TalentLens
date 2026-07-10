"use client"

import { Skeleton } from "@/components/ui/skeleton"
import { DashboardErrorState } from "@/features/dashboard"
import { useAssessmentConfig } from "@/hooks"

import { AssessmentConfigForm } from "./assessment-config-form"

function AssessmentSettingsPanel() {
  const { data: config, isPending, isError, error, refetch } = useAssessmentConfig()

  if (isPending) {
    return <Skeleton className="h-64 w-full" />
  }

  if (isError) {
    return <DashboardErrorState error={error} onRetry={() => void refetch()} />
  }

  return <AssessmentConfigForm config={config} />
}

export { AssessmentSettingsPanel }
