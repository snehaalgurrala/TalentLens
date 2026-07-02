"use client"

import { X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useOrgMembers } from "@/hooks"
import type { CampaignFilters as CampaignFiltersValue } from "@/types"

import {
  CAMPAIGN_PRIORITY_OPTIONS,
  CAMPAIGN_STATUS_OPTIONS,
  EMPLOYMENT_TYPE_OPTIONS,
} from "./constants"

export interface CampaignFiltersProps {
  filters: CampaignFiltersValue
  onChange: (filters: CampaignFiltersValue) => void
}

const ALL = "__all__"

function CampaignFilters({ filters, onChange }: CampaignFiltersProps) {
  const membersQuery = useOrgMembers()
  const members = membersQuery.data ?? []

  const hasActiveFilters = Boolean(
    filters.status ||
      filters.department ||
      filters.employment_type ||
      filters.priority ||
      filters.recruiter_id ||
      filters.hiring_manager_id ||
      filters.created_after ||
      filters.created_before
  )

  function update(patch: Partial<CampaignFiltersValue>) {
    onChange({ ...filters, ...patch, skip: 0 })
  }

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="filter-status">Status</Label>
        <Select
          value={filters.status ?? ALL}
          onValueChange={(value) => update({ status: value === ALL ? undefined : (value as CampaignFiltersValue["status"]) })}
        >
          <SelectTrigger id="filter-status" className="w-36">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All statuses</SelectItem>
            {CAMPAIGN_STATUS_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="filter-department">Department</Label>
        <Input
          id="filter-department"
          placeholder="Any department"
          className="w-40"
          value={filters.department ?? ""}
          onChange={(event) => update({ department: event.target.value || undefined })}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="filter-employment-type">Employment type</Label>
        <Select
          value={filters.employment_type ?? ALL}
          onValueChange={(value) =>
            update({ employment_type: value === ALL ? undefined : (value as CampaignFiltersValue["employment_type"]) })
          }
        >
          <SelectTrigger id="filter-employment-type" className="w-36">
            <SelectValue placeholder="Any type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Any type</SelectItem>
            {EMPLOYMENT_TYPE_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="filter-priority">Priority</Label>
        <Select
          value={filters.priority ?? ALL}
          onValueChange={(value) => update({ priority: value === ALL ? undefined : (value as CampaignFiltersValue["priority"]) })}
        >
          <SelectTrigger id="filter-priority" className="w-32">
            <SelectValue placeholder="Any priority" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Any priority</SelectItem>
            {CAMPAIGN_PRIORITY_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="filter-recruiter">Recruiter</Label>
        <Select
          value={filters.recruiter_id ?? ALL}
          onValueChange={(value) => update({ recruiter_id: value === ALL ? undefined : value })}
        >
          <SelectTrigger id="filter-recruiter" className="w-40">
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

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="filter-hiring-manager">Hiring manager</Label>
        <Select
          value={filters.hiring_manager_id ?? ALL}
          onValueChange={(value) => update({ hiring_manager_id: value === ALL ? undefined : value })}
        >
          <SelectTrigger id="filter-hiring-manager" className="w-40">
            <SelectValue placeholder="Any manager" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Any manager</SelectItem>
            {members.map((member) => (
              <SelectItem key={member.id} value={member.id}>
                {member.full_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="filter-created-after">Created after</Label>
        <Input
          id="filter-created-after"
          type="date"
          className="w-40"
          value={filters.created_after ?? ""}
          onChange={(event) => update({ created_after: event.target.value || undefined })}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="filter-created-before">Created before</Label>
        <Input
          id="filter-created-before"
          type="date"
          className="w-40"
          value={filters.created_before ?? ""}
          onChange={(event) => update({ created_before: event.target.value || undefined })}
        />
      </div>

      {hasActiveFilters && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() =>
            update({
              status: undefined,
              department: undefined,
              employment_type: undefined,
              priority: undefined,
              recruiter_id: undefined,
              hiring_manager_id: undefined,
              created_after: undefined,
              created_before: undefined,
            })
          }
        >
          <X className="size-4" aria-hidden="true" />
          Clear filters
        </Button>
      )}
    </div>
  )
}

export { CampaignFilters }
