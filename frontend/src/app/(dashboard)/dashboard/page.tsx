import type { Metadata } from "next"

import { PageContainer } from "@/layouts/page-container"
import { DashboardView } from "@/features/dashboard"

export const metadata: Metadata = { title: "Dashboard" }

export default function DashboardPage() {
  return (
    <PageContainer title="Dashboard" description="Your recruitment activity at a glance.">
      <DashboardView />
    </PageContainer>
  )
}
