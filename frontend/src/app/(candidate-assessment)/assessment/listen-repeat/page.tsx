import type { Metadata } from "next"

import { ListenRepeatScreen } from "@/features/candidate-runner"

export const metadata: Metadata = { title: "Listen & Repeat" }

export default function ListenRepeatPage() {
  return <ListenRepeatScreen />
}
