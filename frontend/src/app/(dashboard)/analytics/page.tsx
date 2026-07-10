import type { Metadata } from "next"

import { AssessmentAnalyticsView } from "@/features/assessment-analytics"
import { PageContainer } from "@/layouts/page-container"

export const metadata: Metadata = { title: "Analytics" }

export default function AnalyticsPage() {
  return (
    <PageContainer title="Analytics" description="Track assessment performance over time.">
      <AssessmentAnalyticsView />
    </PageContainer>
  )
}
