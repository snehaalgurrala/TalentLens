import type { Metadata } from "next"

import { PageContainer } from "@/layouts/page-container"

export const metadata: Metadata = { title: "Analytics" }

export default function AnalyticsPage() {
  return (
    <PageContainer title="Analytics" description="Track hiring performance over time.">
      <p className="text-sm text-muted-foreground">Charts ship in a later phase.</p>
    </PageContainer>
  )
}
