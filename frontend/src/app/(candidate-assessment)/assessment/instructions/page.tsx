import type { Metadata } from "next"

import { InstructionsScreen } from "@/features/candidate-runner"

export const metadata: Metadata = { title: "Instructions" }

export default function InstructionsPage() {
  return <InstructionsScreen />
}
