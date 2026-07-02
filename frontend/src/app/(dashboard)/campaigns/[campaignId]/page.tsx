import type { Metadata } from "next"

import { PageContainer } from "@/layouts/page-container"
import { CampaignDetailsView } from "@/features/campaigns"

export const metadata: Metadata = { title: "Campaign Details" }

interface CampaignDetailsPageProps {
  params: Promise<{ campaignId: string }>
}

export default async function CampaignDetailsPage({ params }: CampaignDetailsPageProps) {
  const { campaignId } = await params

  return (
    <PageContainer
      title="Campaign Details"
      description="Overview, job description, resumes, and candidates for this campaign."
    >
      <CampaignDetailsView campaignId={campaignId} />
    </PageContainer>
  )
}
