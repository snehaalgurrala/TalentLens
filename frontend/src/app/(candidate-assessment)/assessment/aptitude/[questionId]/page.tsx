import type { Metadata } from "next"
import { notFound } from "next/navigation"

import { AptitudeQuestionScreen } from "@/features/candidate-runner"

export const metadata: Metadata = { title: "Aptitude" }

interface AptitudeQuestionPageProps {
  params: Promise<{ questionId: string }>
}

export default async function AptitudeQuestionPage({ params }: AptitudeQuestionPageProps) {
  const { questionId } = await params
  const parsed = Number(questionId)

  if (!Number.isInteger(parsed) || parsed < 1 || parsed > 5) {
    notFound()
  }

  return <AptitudeQuestionScreen questionId={parsed} />
}
