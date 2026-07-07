import type { Metadata } from "next"

import { CompletionScreen } from "@/features/candidate-runner"

export const metadata: Metadata = { title: "Assessment Complete" }

export default function CompletedPage() {
  return <CompletionScreen />
}
