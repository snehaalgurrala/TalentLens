import type { Metadata } from "next"

import { ReadAloudScreen } from "@/features/candidate-runner"

export const metadata: Metadata = { title: "Read Aloud" }

export default function ReadAloudPage() {
  return <ReadAloudScreen />
}
