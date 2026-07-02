import type { Metadata } from "next"

import { PageContainer } from "@/layouts/page-container"
import { CampaignsListView } from "@/features/campaigns"

export const metadata: Metadata = { title: "Campaigns" }

export default function CampaignsPage() {
  return (
    <PageContainer title="Campaigns" description="Manage your recruitment campaigns.">
      <CampaignsListView />
    </PageContainer>
  )
}
