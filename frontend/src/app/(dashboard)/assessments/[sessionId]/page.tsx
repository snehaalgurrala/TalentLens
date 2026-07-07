import type { Metadata } from "next"

import { PageContainer } from "@/layouts/page-container"
import { AssessmentDashboardView } from "@/features/assessment-dashboard"

export const metadata: Metadata = { title: "Assessment Results" }

interface AssessmentDashboardPageProps {
  params: Promise<{ sessionId: string }>
}

export default async function AssessmentDashboardPage({ params }: AssessmentDashboardPageProps) {
  const { sessionId } = await params

  return (
    <PageContainer
      title="Assessment Results"
      description="Communication assessment results, transcripts, recordings, and processing status."
    >
      <AssessmentDashboardView sessionId={sessionId} />
    </PageContainer>
  )
}
