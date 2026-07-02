"use client"

import * as React from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { Controller, useForm } from "react-hook-form"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { useCreateCampaign, useOrgMembers, useUpdateCampaign } from "@/hooks"
import type { Campaign, CampaignCreate } from "@/types"

import {
  CAMPAIGN_PRIORITY_OPTIONS,
  CAMPAIGN_STATUS_OPTIONS,
  EMPLOYMENT_TYPE_OPTIONS,
} from "./constants"
import { campaignFormSchema, type CampaignFormValues } from "./schemas"

export interface CampaignFormProps {
  mode: "create" | "edit"
  campaign?: Campaign
  open: boolean
  onOpenChange: (open: boolean) => void
}

const NONE = "__none__"

function campaignToFormValues(campaign?: Campaign): CampaignFormValues {
  if (!campaign) {
    return {
      title: "",
      job_title: "",
      description: "",
      department: "",
      hiring_manager_id: "",
      recruiter_id: "",
      employment_type: "",
      location: "",
      experience_min_years: "",
      experience_max_years: "",
      salary_min: "",
      salary_max: "",
      openings_count: "1",
      priority: "MEDIUM",
      closing_date: "",
      status: "DRAFT",
    }
  }
  return {
    title: campaign.title,
    job_title: campaign.job_title ?? "",
    description: campaign.description ?? "",
    department: campaign.department ?? "",
    hiring_manager_id: campaign.hiring_manager_id ?? "",
    recruiter_id: campaign.recruiter_id ?? "",
    employment_type: campaign.employment_type ?? "",
    location: campaign.location ?? "",
    experience_min_years: campaign.experience_min_years?.toString() ?? "",
    experience_max_years: campaign.experience_max_years?.toString() ?? "",
    salary_min: campaign.salary_min?.toString() ?? "",
    salary_max: campaign.salary_max?.toString() ?? "",
    openings_count: campaign.openings_count.toString(),
    priority: campaign.priority,
    closing_date: campaign.closing_date ?? "",
    status: campaign.status,
  }
}

function toPayload(values: CampaignFormValues): CampaignCreate {
  return {
    title: values.title.trim(),
    job_title: values.job_title || null,
    description: values.description || null,
    department: values.department || null,
    hiring_manager_id: values.hiring_manager_id || null,
    recruiter_id: values.recruiter_id || null,
    employment_type: values.employment_type || null,
    location: values.location || null,
    experience_min_years:
      values.experience_min_years === "" ? null : Number(values.experience_min_years),
    experience_max_years:
      values.experience_max_years === "" ? null : Number(values.experience_max_years),
    salary_min: values.salary_min === "" ? null : Number(values.salary_min),
    salary_max: values.salary_max === "" ? null : Number(values.salary_max),
    openings_count: Number(values.openings_count),
    priority: values.priority,
    closing_date: values.closing_date || null,
    status: values.status,
  }
}

function CampaignForm({ mode, campaign, open, onOpenChange }: CampaignFormProps) {
  const membersQuery = useOrgMembers()
  const members = membersQuery.data ?? []
  const createCampaign = useCreateCampaign()
  const updateCampaign = useUpdateCampaign(campaign?.id ?? "")

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CampaignFormValues>({
    resolver: zodResolver(campaignFormSchema),
    defaultValues: campaignToFormValues(campaign),
  })

  React.useEffect(() => {
    if (open) reset(campaignToFormValues(campaign))
  }, [open, campaign, reset])

  async function onSubmit(values: CampaignFormValues) {
    const payload = toPayload(values)
    try {
      if (mode === "edit" && campaign) {
        await updateCampaign.mutateAsync(payload)
        toast.success("Campaign updated")
      } else {
        await createCampaign.mutateAsync(payload)
        toast.success("Campaign created")
      }
      onOpenChange(false)
    } catch (error) {
      const message = error instanceof Error ? error.message : "Something went wrong"
      toast.error(message)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <form noValidate onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>{mode === "edit" ? "Edit Campaign" : "New Campaign"}</DialogTitle>
            <DialogDescription>
              {mode === "edit"
                ? "Update this campaign's details."
                : "Set up a new hiring campaign to start collecting resumes."}
            </DialogDescription>
          </DialogHeader>

          <div className="grid max-h-[60vh] grid-cols-1 gap-4 overflow-y-auto p-1 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5 sm:col-span-2">
              <Label htmlFor="campaign-title">Campaign Name</Label>
              <Input id="campaign-title" aria-invalid={!!errors.title} {...register("title")} />
              {errors.title && <p className="text-xs text-destructive">{errors.title.message}</p>}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="campaign-job-title">Job Title</Label>
              <Input id="campaign-job-title" {...register("job_title")} />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="campaign-department">Department</Label>
              <Input id="campaign-department" {...register("department")} />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="campaign-hiring-manager">Hiring Manager</Label>
              <Controller
                control={control}
                name="hiring_manager_id"
                render={({ field }) => (
                  <Select
                    value={field.value || NONE}
                    onValueChange={(value) => field.onChange(value === NONE ? "" : value)}
                  >
                    <SelectTrigger id="campaign-hiring-manager" className="w-full">
                      <SelectValue placeholder="Unassigned" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={NONE}>Unassigned</SelectItem>
                      {members.map((member) => (
                        <SelectItem key={member.id} value={member.id}>
                          {member.full_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="campaign-recruiter">Recruiter</Label>
              <Controller
                control={control}
                name="recruiter_id"
                render={({ field }) => (
                  <Select
                    value={field.value || NONE}
                    onValueChange={(value) => field.onChange(value === NONE ? "" : value)}
                  >
                    <SelectTrigger id="campaign-recruiter" className="w-full">
                      <SelectValue placeholder="Unassigned" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={NONE}>Unassigned</SelectItem>
                      {members.map((member) => (
                        <SelectItem key={member.id} value={member.id}>
                          {member.full_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="campaign-employment-type">Employment Type</Label>
              <Controller
                control={control}
                name="employment_type"
                render={({ field }) => (
                  <Select
                    value={field.value || NONE}
                    onValueChange={(value) => field.onChange(value === NONE ? "" : value)}
                  >
                    <SelectTrigger id="campaign-employment-type" className="w-full">
                      <SelectValue placeholder="Not specified" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={NONE}>Not specified</SelectItem>
                      {EMPLOYMENT_TYPE_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="campaign-location">Location</Label>
              <Input id="campaign-location" {...register("location")} />
            </div>

            <div className="flex gap-2">
              <div className="flex flex-1 flex-col gap-1.5">
                <Label htmlFor="campaign-exp-min">Experience (min yrs)</Label>
                <Input id="campaign-exp-min" type="number" min={0} {...register("experience_min_years")} />
              </div>
              <div className="flex flex-1 flex-col gap-1.5">
                <Label htmlFor="campaign-exp-max">Experience (max yrs)</Label>
                <Input id="campaign-exp-max" type="number" min={0} {...register("experience_max_years")} />
              </div>
            </div>
            {errors.experience_max_years && (
              <p className="text-xs text-destructive sm:col-span-2">
                {errors.experience_max_years.message}
              </p>
            )}

            <div className="flex gap-2">
              <div className="flex flex-1 flex-col gap-1.5">
                <Label htmlFor="campaign-salary-min">Salary Min</Label>
                <Input id="campaign-salary-min" type="number" min={0} {...register("salary_min")} />
              </div>
              <div className="flex flex-1 flex-col gap-1.5">
                <Label htmlFor="campaign-salary-max">Salary Max</Label>
                <Input id="campaign-salary-max" type="number" min={0} {...register("salary_max")} />
              </div>
            </div>
            {errors.salary_max && (
              <p className="text-xs text-destructive sm:col-span-2">{errors.salary_max.message}</p>
            )}

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="campaign-openings">Number of Openings</Label>
              <Input id="campaign-openings" type="number" min={1} {...register("openings_count")} />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="campaign-priority">Priority</Label>
              <Controller
                control={control}
                name="priority"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger id="campaign-priority" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CAMPAIGN_PRIORITY_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="campaign-closing-date">Closing Date</Label>
              <Input id="campaign-closing-date" type="date" {...register("closing_date")} />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="campaign-status">Status</Label>
              <Controller
                control={control}
                name="status"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger id="campaign-status" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CAMPAIGN_STATUS_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>

            <div className="flex flex-col gap-1.5 sm:col-span-2">
              <Label htmlFor="campaign-description">Description</Label>
              <Textarea id="campaign-description" rows={4} {...register("description")} />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              {mode === "edit" ? "Save Changes" : "Create Campaign"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export { CampaignForm }
