import type { Metadata } from "next"

import { DeviceCheckScreen } from "@/features/candidate-runner"

export const metadata: Metadata = { title: "Device Check" }

export default function DeviceCheckPage() {
  return <DeviceCheckScreen />
}
