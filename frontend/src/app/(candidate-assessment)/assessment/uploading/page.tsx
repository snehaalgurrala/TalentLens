import type { Metadata } from "next"

import { UploadingScreen } from "@/features/candidate-runner"

export const metadata: Metadata = { title: "Submitting Assessment" }

export default function UploadingPage() {
  return <UploadingScreen />
}
