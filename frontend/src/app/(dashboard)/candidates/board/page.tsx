import type { Metadata } from "next"

import { PageContainer } from "@/layouts/page-container"
import { PipelineBoardView } from "@/features/pipeline-board"

export const metadata: Metadata = { title: "Pipeline Board" }

export default function CandidatesBoardPage() {
  return (
    <PageContainer
      title="Pipeline Board"
      description="Candidates move between stages automatically as they progress."
    >
      <PipelineBoardView />
    </PageContainer>
  )
}
