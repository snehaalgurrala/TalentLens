"use client"

import * as React from "react"
import { Archive, Copy, Download, MoreHorizontal, Pencil, Trash2, XCircle } from "lucide-react"
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useCreateCampaign, useDeleteCampaign, useUpdateCampaign } from "@/hooks"
import { candidateService } from "@/services/candidate.service"
import { downloadCsv, toCsv } from "@/utils"
import type { ApiError, Campaign } from "@/types"

import { CampaignForm } from "./campaign-form"

export interface CampaignActionsMenuProps {
  campaign: Campaign
}

function CampaignActionsMenu({ campaign }: CampaignActionsMenuProps) {
  const [editOpen, setEditOpen] = React.useState(false)
  const [deleteOpen, setDeleteOpen] = React.useState(false)
  const [isDownloading, setIsDownloading] = React.useState(false)

  const updateCampaign = useUpdateCampaign(campaign.id)
  const deleteCampaign = useDeleteCampaign()
  const createCampaign = useCreateCampaign()

  function handleArchive() {
    updateCampaign.mutate(
      { status: "ARCHIVED" },
      {
        onSuccess: () => toast.success(`"${campaign.title}" archived`),
        onError: (error) => toast.error(error.message || "Failed to archive campaign"),
      }
    )
  }

  function handleClose() {
    updateCampaign.mutate(
      { status: "CLOSED" },
      {
        onSuccess: () => toast.success(`"${campaign.title}" closed`),
        onError: (error) => toast.error(error.message || "Failed to close campaign"),
      }
    )
  }

  function handleDuplicate() {
    createCampaign.mutate(
      {
        title: `${campaign.title} (Copy)`,
        job_title: campaign.job_title,
        description: campaign.description,
        department: campaign.department,
        hiring_manager_id: campaign.hiring_manager_id,
        recruiter_id: campaign.recruiter_id,
        employment_type: campaign.employment_type,
        location: campaign.location,
        experience_min_years: campaign.experience_min_years,
        experience_max_years: campaign.experience_max_years,
        salary_min: campaign.salary_min,
        salary_max: campaign.salary_max,
        openings_count: campaign.openings_count,
        priority: campaign.priority,
        status: "DRAFT",
      },
      {
        onSuccess: () => toast.success(`"${campaign.title}" duplicated`),
        onError: (error) => toast.error(error.message || "Failed to duplicate campaign"),
      }
    )
  }

  function handleDelete() {
    deleteCampaign.mutate(campaign.id, {
      onSuccess: () => {
        toast.success(`"${campaign.title}" deleted`)
        setDeleteOpen(false)
      },
      onError: (error) => {
        toast.error(error.message || "Failed to delete campaign")
        setDeleteOpen(false)
      },
    })
  }

  async function handleDownloadReport() {
    setIsDownloading(true)
    try {
      const rankings = await candidateService.listRankings(campaign.id)
      const csv = toCsv(rankings, [
        { header: "Rank", value: (r) => r.rank },
        { header: "Candidate", value: (r) => r.candidate_name },
        { header: "Match Score", value: (r) => r.overall_score },
        { header: "Recommendation", value: (r) => r.recommendation },
      ])
      downloadCsv(`${campaign.title.replace(/\s+/g, "-").toLowerCase()}-candidate-report.csv`, csv)
    } catch (error) {
      const apiError = error as ApiError
      toast.error(
        apiError.status === 422
          ? "This campaign has no ranked candidates yet — add a job description and resumes first."
          : apiError.message || "Failed to generate report"
      )
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon-sm" aria-label={`Actions for ${campaign.title}`}>
            <MoreHorizontal className="size-4" aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onSelect={() => setEditOpen(true)}>
            <Pencil aria-hidden="true" />
            Edit Campaign
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={handleDuplicate}>
            <Copy aria-hidden="true" />
            Duplicate Campaign
          </DropdownMenuItem>
          {campaign.status !== "ARCHIVED" && (
            <DropdownMenuItem onSelect={handleArchive}>
              <Archive aria-hidden="true" />
              Archive
            </DropdownMenuItem>
          )}
          {campaign.status !== "CLOSED" && (
            <DropdownMenuItem onSelect={handleClose}>
              <XCircle aria-hidden="true" />
              Close Campaign
            </DropdownMenuItem>
          )}
          <DropdownMenuItem onSelect={handleDownloadReport} disabled={isDownloading}>
            <Download aria-hidden="true" />
            Download Candidate Report
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem variant="destructive" onSelect={() => setDeleteOpen(true)}>
            <Trash2 aria-hidden="true" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <CampaignForm mode="edit" campaign={campaign} open={editOpen} onOpenChange={setEditOpen} />

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete campaign?</DialogTitle>
            <DialogDescription>
              &ldquo;{campaign.title}&rdquo; will be moved to trash. This can be reversed by an
              administrator, but the campaign will no longer appear in your list.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" isLoading={deleteCampaign.isPending} onClick={handleDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

export { CampaignActionsMenu }
