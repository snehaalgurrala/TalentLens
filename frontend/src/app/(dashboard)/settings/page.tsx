import type { Metadata } from "next"
import { Suspense } from "react"

import { Skeleton } from "@/components/ui/skeleton"
import { SettingsView } from "@/features/settings"
import { PageContainer } from "@/layouts/page-container"

export const metadata: Metadata = { title: "Settings" }

export default function SettingsPage() {
  return (
    <PageContainer title="Settings" description="Manage organization, platform, and account configuration.">
      <Suspense fallback={<Skeleton className="h-96 w-full" />}>
        <SettingsView />
      </Suspense>
    </PageContainer>
  )
}
