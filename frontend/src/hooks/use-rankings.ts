import { useQuery } from "@tanstack/react-query"

import { candidateService } from "@/services/candidate.service"
import type { ApiError, CandidateRanking } from "@/types"

export const rankingKeys = {
  all: ["rankings"] as const,
  byCampaign: (campaignId: string) => [...rankingKeys.all, campaignId] as const,
}

export function useCampaignRankings(campaignId: string | undefined) {
  return useQuery<CandidateRanking[], ApiError>({
    queryKey: rankingKeys.byCampaign(campaignId ?? ""),
    queryFn: () => candidateService.listRankings(campaignId as string),
    enabled: Boolean(campaignId),
    retry: false,
  })
}
