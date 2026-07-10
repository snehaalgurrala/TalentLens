import type { Metadata } from "next"

import { InvitationEntryScreen } from "@/features/candidate-runner"

export const metadata: Metadata = { title: "Assessment" }

interface InvitationEntryPageProps {
  params: Promise<{ token: string }>
}

export default async function InvitationEntryPage({ params }: InvitationEntryPageProps) {
  const { token } = await params

  return <InvitationEntryScreen token={token} />
}
