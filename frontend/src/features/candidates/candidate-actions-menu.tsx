"use client"

import * as React from "react"
import {
  Archive,
  CheckCircle2,
  Download,
  MoreHorizontal,
  NotebookPen,
  RotateCcw,
  Send,
  Trash2,
  UserPlus,
  Workflow,
  XCircle,
} from "lucide-react"
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
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import {
  useArchiveCandidate,
  useAssignRecruiter,
  useDeleteCandidate,
  useOrgMembers,
  useRejectCandidate,
  useRestoreCandidate,
  useShortlistCandidate,
  useUpdatePipelineStage,
} from "@/hooks"
import { candidateService } from "@/services/candidate.service"
import { downloadBlob } from "@/utils"
import type { CandidateListItem, PipelineStage } from "@/types"

import { PIPELINE_STAGE_OPTIONS, TERMINAL_STAGES } from "./constants"

export interface CandidateActionsMenuProps {
  candidate: CandidateListItem
  onEditNotes: (candidate: CandidateListItem) => void
}

function CandidateActionsMenu({ candidate, onEditNotes }: CandidateActionsMenuProps) {
  const [assignOpen, setAssignOpen] = React.useState(false)
  const [deleteOpen, setDeleteOpen] = React.useState(false)
  const [isDownloading, setIsDownloading] = React.useState(false)
  const [recruiterId, setRecruiterId] = React.useState<string>(candidate.assigned_recruiter?.id ?? "")

  const membersQuery = useOrgMembers()
  const shortlist = useShortlistCandidate()
  const reject = useRejectCandidate()
  const assignRecruiter = useAssignRecruiter()
  const updatePipelineStage = useUpdatePipelineStage()
  const deleteCandidate = useDeleteCandidate()
  const archiveCandidate = useArchiveCandidate()
  const restoreCandidate = useRestoreCandidate()
  const isTerminal = TERMINAL_STAGES.has(candidate.pipeline_stage)

  function handleShortlist() {
    shortlist.mutate(candidate.resume_file_id, {
      onSuccess: () => toast.success(`${candidate.candidate_name} shortlisted`),
      onError: (error) => toast.error(error.message || "Failed to shortlist candidate"),
    })
  }

  function handleReject() {
    reject.mutate(candidate.resume_file_id, {
      onSuccess: () => toast.success(`${candidate.candidate_name} rejected`),
      onError: (error) => toast.error(error.message || "Failed to reject candidate"),
    })
  }

  function handleAssign() {
    assignRecruiter.mutate(
      { resumeFileId: candidate.resume_file_id, recruiterId: recruiterId || null },
      {
        onSuccess: () => {
          toast.success("Recruiter assigned")
          setAssignOpen(false)
        },
        onError: (error) => toast.error(error.message || "Failed to assign recruiter"),
      }
    )
  }

  function handleMoveStage(stage: PipelineStage) {
    updatePipelineStage.mutate(
      { resumeFileId: candidate.resume_file_id, pipelineStage: stage },
      {
        onSuccess: () => toast.success(`Moved to ${stage.replace(/_/g, " ").toLowerCase()}`),
        onError: (error) => toast.error(error.message || "Failed to update pipeline stage"),
      }
    )
  }

  function handleArchive() {
    archiveCandidate.mutate(candidate.resume_file_id, {
      onSuccess: () => toast.success(`${candidate.candidate_name} archived`),
      onError: (error) => toast.error(error.message || "Failed to archive candidate"),
    })
  }

  function handleRestore() {
    restoreCandidate.mutate(candidate.resume_file_id, {
      onSuccess: () => toast.success(`${candidate.candidate_name} restored`),
      onError: (error) => toast.error(error.message || "Failed to restore candidate"),
    })
  }

  function handleDelete() {
    deleteCandidate.mutate(candidate.resume_file_id, {
      onSuccess: () => {
        toast.success(`${candidate.candidate_name} removed`)
        setDeleteOpen(false)
      },
      onError: (error) => {
        toast.error(error.message || "Failed to remove candidate")
        setDeleteOpen(false)
      },
    })
  }

  async function handleDownload() {
    setIsDownloading(true)
    try {
      const { blob, filename } = await candidateService.downloadResume(candidate.resume_file_id)
      downloadBlob(filename, blob)
    } catch {
      toast.error("Failed to download resume")
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon-sm" aria-label={`Actions for ${candidate.candidate_name}`}>
            <MoreHorizontal className="size-4" aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onSelect={handleShortlist} disabled={candidate.review_status === "SHORTLISTED"}>
            <CheckCircle2 aria-hidden="true" />
            Shortlist
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={handleReject} disabled={candidate.review_status === "REJECTED"}>
            <XCircle aria-hidden="true" />
            Reject
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => setAssignOpen(true)}>
            <UserPlus aria-hidden="true" />
            {candidate.assigned_recruiter ? "Transfer Ownership" : "Assign Recruiter"}
          </DropdownMenuItem>
          {isTerminal ? (
            <DropdownMenuItem onSelect={handleRestore} disabled={restoreCandidate.isPending}>
              <RotateCcw aria-hidden="true" />
              Restore
            </DropdownMenuItem>
          ) : (
            <DropdownMenuItem onSelect={handleArchive} disabled={archiveCandidate.isPending}>
              <Archive aria-hidden="true" />
              Archive
            </DropdownMenuItem>
          )}
          <DropdownMenuSub>
            <DropdownMenuSubTrigger>
              <Workflow aria-hidden="true" />
              Move Pipeline Stage
            </DropdownMenuSubTrigger>
            <DropdownMenuSubContent>
              {PIPELINE_STAGE_OPTIONS.map((option) => (
                <DropdownMenuItem
                  key={option.value}
                  onSelect={() => handleMoveStage(option.value)}
                  disabled={candidate.pipeline_stage === option.value}
                >
                  {option.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuSubContent>
          </DropdownMenuSub>
          <DropdownMenuItem onSelect={() => onEditNotes(candidate)}>
            <NotebookPen aria-hidden="true" />
            Add/Edit Notes
          </DropdownMenuItem>
          <Tooltip>
            <TooltipTrigger asChild>
              <div>
                <DropdownMenuItem disabled>
                  <Send aria-hidden="true" />
                  Send Assessment
                </DropdownMenuItem>
              </div>
            </TooltipTrigger>
            <TooltipContent>Coming soon</TooltipContent>
          </Tooltip>
          <DropdownMenuItem onSelect={handleDownload} disabled={isDownloading}>
            <Download aria-hidden="true" />
            Download Resume
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem variant="destructive" onSelect={() => setDeleteOpen(true)}>
            <Trash2 aria-hidden="true" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={assignOpen} onOpenChange={setAssignOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign recruiter</DialogTitle>
            <DialogDescription>Choose who owns {candidate.candidate_name}&rsquo;s review.</DialogDescription>
          </DialogHeader>
          <Select value={recruiterId || "__unassigned__"} onValueChange={(v) => setRecruiterId(v === "__unassigned__" ? "" : v)}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Unassigned" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__unassigned__">Unassigned</SelectItem>
              {(membersQuery.data ?? []).map((member) => (
                <SelectItem key={member.id} value={member.id}>
                  {member.full_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAssignOpen(false)}>
              Cancel
            </Button>
            <Button isLoading={assignRecruiter.isPending} onClick={handleAssign}>
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove candidate?</DialogTitle>
            <DialogDescription>
              &ldquo;{candidate.candidate_name}&rdquo;&apos;s application will be removed from this campaign. This can be
              reversed by an administrator.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" isLoading={deleteCandidate.isPending} onClick={handleDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

export { CandidateActionsMenu }
