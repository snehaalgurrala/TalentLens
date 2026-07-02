import type { Metadata } from "next"

import { PageContainer } from "@/layouts/page-container"

export const metadata: Metadata = { title: "Candidate Profile" }

interface CandidateProfilePageProps {
  params: Promise<{ candidateId: string }>
}

export default async function CandidateProfilePage({ params }: CandidateProfilePageProps) {
  await params

  return (
    <PageContainer title="Candidate Profile" description="Full candidate profile, resume, and AI explanation.">
      <p className="text-sm text-muted-foreground">
        The full candidate profile view ships in a later phase. Use the candidates table to review scores, manage
        pipeline stage, and take actions on this candidate for now.
      </p>
    </PageContainer>
  )
}
