"use client"

import Link from "next/link"
import { RefreshCw, Upload } from "lucide-react"

import { Button } from "@/components/ui/button"
import { SearchInput } from "@/components/ui/search-input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { Campaign, CandidateListFilters } from "@/types"

import { CandidatesFilterDrawer } from "./candidates-filter-drawer"

export interface CandidatesToolbarProps {
  campaigns: Campaign[]
  selectedCampaignId: string | null
  onCampaignChange: (campaignId: string) => void
  searchInput: string
  onSearchChange: (value: string) => void
  filters: CandidateListFilters
  onFiltersChange: (filters: CandidateListFilters) => void
  filterDrawerOpen: boolean
  onFilterDrawerOpenChange: (open: boolean) => void
  onRefresh: () => void
  onExportCsv: () => void
  exportDisabled: boolean
}

function CandidatesToolbar({
  campaigns,
  selectedCampaignId,
  onCampaignChange,
  searchInput,
  onSearchChange,
  filters,
  onFiltersChange,
  filterDrawerOpen,
  onFilterDrawerOpenChange,
  onRefresh,
  onExportCsv,
  exportDisabled,
}: CandidatesToolbarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Select value={selectedCampaignId ?? undefined} onValueChange={onCampaignChange}>
        <SelectTrigger className="w-56">
          <SelectValue placeholder="Select a campaign" />
        </SelectTrigger>
        <SelectContent>
          {campaigns.map((campaign) => (
            <SelectItem key={campaign.id} value={campaign.id}>
              {campaign.title}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <div className="min-w-64 flex-1">
        <SearchInput
          placeholder="Search name, email, phone, company, skills, college..."
          value={searchInput}
          onChange={(event) => onSearchChange(event.target.value)}
          onClear={() => onSearchChange("")}
        />
      </div>

      <CandidatesFilterDrawer
        filters={filters}
        onChange={onFiltersChange}
        open={filterDrawerOpen}
        onOpenChange={onFilterDrawerOpenChange}
      />

      <Button variant="outline" size="sm" onClick={onRefresh}>
        <RefreshCw className="size-4" aria-hidden="true" />
        Refresh
      </Button>

      <Button variant="outline" size="sm" onClick={onExportCsv} disabled={exportDisabled}>
        Export CSV
      </Button>

      {selectedCampaignId && (
        <Button variant="outline" size="sm" asChild>
          <Link href={`/campaigns/${selectedCampaignId}`}>
            <Upload className="size-4" aria-hidden="true" />
            Upload Resumes
          </Link>
        </Button>
      )}
    </div>
  )
}

export { CandidatesToolbar }
