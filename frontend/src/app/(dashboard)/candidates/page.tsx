import type { Metadata } from "next"

import { PageContainer } from "@/layouts/page-container"
import { CandidatesListView } from "@/features/candidates"

export const metadata: Metadata = { title: "Candidates" }

export default function CandidatesPage() {
  return (
    <PageContainer title="Candidates" description="Review and rank incoming candidates.">
      <CandidatesListView />
    </PageContainer>
  )
}
