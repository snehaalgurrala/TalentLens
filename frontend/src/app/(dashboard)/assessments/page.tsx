import type { Metadata } from "next"

import { PageContainer } from "@/layouts/page-container"

export const metadata: Metadata = { title: "Assessments" }

export default function AssessmentsPage() {
  return (
    <PageContainer title="Assessments" description="Configure candidate assessments.">
      <p className="text-sm text-muted-foreground">Assessment tooling ships in a later phase.</p>
    </PageContainer>
  )
}
