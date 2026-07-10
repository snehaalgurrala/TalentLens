import type { Metadata } from "next"

import { ProfileView } from "@/features/profile"
import { PageContainer } from "@/layouts/page-container"

export const metadata: Metadata = { title: "Profile" }

export default function ProfilePage() {
  return (
    <PageContainer title="Profile" description="Your personal account details.">
      <ProfileView />
    </PageContainer>
  )
}
