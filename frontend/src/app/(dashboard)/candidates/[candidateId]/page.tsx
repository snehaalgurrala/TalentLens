import type { Metadata } from "next"

import { PageContainer } from "@/layouts/page-container"
import { CandidateProfileView } from "@/features/candidate-profile"

export const metadata: Metadata = { title: "Candidate Profile" }

interface CandidateProfilePageProps {
  params: Promise<{ candidateId: string }>
}

export default async function CandidateProfilePage({ params }: CandidateProfilePageProps) {
  const { candidateId } = await params

  return (
    <PageContainer title="Candidate Profile" description="Full candidate profile, resume, and AI explanation.">
      <CandidateProfileView candidateId={candidateId} />
    </PageContainer>
  )
}
