import type { Metadata } from "next"
import { Suspense } from "react"

import { LandingScreen } from "@/features/candidate-runner"

export const metadata: Metadata = { title: "Assessment" }

export default function AssessmentLandingPage() {
  return (
    <Suspense fallback={null}>
      <LandingScreen />
    </Suspense>
  )
}
