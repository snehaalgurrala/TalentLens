import type { Metadata } from "next"

import { PageContainer } from "@/layouts/page-container"

export const metadata: Metadata = { title: "Settings" }

export default function SettingsPage() {
  return (
    <PageContainer title="Settings" description="Manage organization and account settings.">
      <p className="text-sm text-muted-foreground">Settings panels ship in a later phase.</p>
    </PageContainer>
  )
}
