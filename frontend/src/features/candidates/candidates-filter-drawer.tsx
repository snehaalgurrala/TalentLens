"use client"

import { Filter } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { useOrgMembers } from "@/hooks"
import type { CandidateListFilters } from "@/types"

import { PIPELINE_STAGE_OPTIONS, REVIEW_STATUS_OPTIONS } from "./constants"

export interface CandidatesFilterDrawerProps {
  filters: CandidateListFilters
  onChange: (filters: CandidateListFilters) => void
  open: boolean
  onOpenChange: (open: boolean) => void
}

const ALL = "__all__"

function CandidatesFilterDrawer({ filters, onChange, open, onOpenChange }: CandidatesFilterDrawerProps) {
  const membersQuery = useOrgMembers()
  const members = membersQuery.data ?? []

  function update(patch: Partial<CandidateListFilters>) {
    onChange({ ...filters, ...patch, skip: 0 })
  }

  function reset() {
    onChange({
      ...filters,
      pipeline_stage: undefined,
      review_status: undefined,
      assigned_recruiter_id: undefined,
      skip: 0,
    })
  }

  const hasActiveFilters = Boolean(
    filters.pipeline_stage || filters.review_status || filters.assigned_recruiter_id
  )

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm">
          <Filter className="size-4" aria-hidden="true" />
          Filters
          {hasActiveFilters && (
            <span className="ml-1 flex size-4 items-center justify-center rounded-full bg-primary text-[10px] text-primary-foreground">
              •
            </span>
          )}
        </Button>
      </SheetTrigger>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>Filter candidates</SheetTitle>
          <SheetDescription>Narrow down the candidate list for this campaign.</SheetDescription>
        </SheetHeader>

        <div className="flex flex-1 flex-col gap-4 overflow-y-auto">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="filter-pipeline-stage">Pipeline stage</Label>
            <Select
              value={filters.pipeline_stage ?? ALL}
              onValueChange={(value) =>
                update({ pipeline_stage: value === ALL ? undefined : (value as CandidateListFilters["pipeline_stage"]) })
              }
            >
              <SelectTrigger id="filter-pipeline-stage" className="w-full">
                <SelectValue placeholder="Any stage" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>Any stage</SelectItem>
                {PIPELINE_STAGE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="filter-review-status">Resume status</Label>
            <Select
              value={filters.review_status ?? ALL}
              onValueChange={(value) =>
                update({ review_status: value === ALL ? undefined : (value as CandidateListFilters["review_status"]) })
              }
            >
              <SelectTrigger id="filter-review-status" className="w-full">
                <SelectValue placeholder="Any status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>Any status</SelectItem>
                {REVIEW_STATUS_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="filter-recruiter">Assigned recruiter</Label>
            <Select
              value={filters.assigned_recruiter_id ?? ALL}
              onValueChange={(value) => update({ assigned_recruiter_id: value === ALL ? undefined : value })}
            >
              <SelectTrigger id="filter-recruiter" className="w-full">
                <SelectValue placeholder="Any recruiter" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>Any recruiter</SelectItem>
                {members.map((member) => (
                  <SelectItem key={member.id} value={member.id}>
                    {member.full_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <SheetFooter>
          <Button variant="ghost" onClick={reset} disabled={!hasActiveFilters}>
            Reset filters
          </Button>
          <Button onClick={() => onOpenChange(false)}>Done</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}

export { CandidatesFilterDrawer }
