"use client"

import { Skeleton } from "@/components/ui/skeleton"
import { DashboardErrorState } from "@/features/dashboard"
import { useOrganizationSettings } from "@/hooks"

import { OrganizationForm } from "./organization-form"

function OrganizationSettingsPanel() {
  const { data: organization, isPending, isError, error, refetch } = useOrganizationSettings()

  if (isPending) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (isError) {
    return <DashboardErrorState error={error} onRetry={() => void refetch()} />
  }

  return <OrganizationForm organization={organization} />
}

export { OrganizationSettingsPanel }
