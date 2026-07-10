import type { Metadata } from "next"

import { AssessmentsListView } from "@/features/assessments"
import { PageContainer } from "@/layouts/page-container"

export const metadata: Metadata = { title: "Assessments" }

export default function AssessmentsPage() {
  return (
    <PageContainer title="Assessments" description="Review candidate assessment results.">
      <AssessmentsListView />
    </PageContainer>
  )
}
