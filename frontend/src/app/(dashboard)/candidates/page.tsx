import type { Metadata } from "next"

import { PageContainer } from "@/layouts/page-container"

export const metadata: Metadata = { title: "Candidates" }

export default function CandidatesPage() {
  return (
    <PageContainer title="Candidates" description="Review and rank incoming candidates.">
      <p className="text-sm text-muted-foreground">Candidate tables ship in a later phase.</p>
    </PageContainer>
  )
}
