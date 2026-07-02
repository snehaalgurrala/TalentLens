import type { Metadata } from "next"

import { PageContainer } from "@/layouts/page-container"

export const metadata: Metadata = { title: "Profile" }

export default function ProfilePage() {
  return (
    <PageContainer title="Profile" description="Your personal account details.">
      <p className="text-sm text-muted-foreground">Profile editing ships in a later phase.</p>
    </PageContainer>
  )
}
