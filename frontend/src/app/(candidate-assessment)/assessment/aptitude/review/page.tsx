import type { Metadata } from "next"

import { AptitudeReviewScreen } from "@/features/candidate-runner"

export const metadata: Metadata = { title: "Review Answers" }

export default function AptitudeReviewPage() {
  return <AptitudeReviewScreen />
}
