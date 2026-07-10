"use client"

import { Skeleton } from "@/components/ui/skeleton"
import { DashboardErrorState } from "@/features/dashboard"
import { useRecruitmentSettings } from "@/hooks"

import { RankingWeightageCard } from "./ranking-weightage-card"
import { ResumePolicyCard } from "./resume-policy-card"

function RecruitmentSettingsPanel() {
  const { data: settings, isPending, isError, error, refetch } = useRecruitmentSettings()

  return (
    <div className="flex flex-col gap-6">
      <RankingWeightageCard />

      {isPending && <Skeleton className="h-72 w-full" />}
      {isError && <DashboardErrorState error={error} onRetry={() => void refetch()} />}
      {!isPending && !isError && <ResumePolicyCard settings={settings} />}
    </div>
  )
}

export { RecruitmentSettingsPanel }
