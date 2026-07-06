"use client"

import * as React from "react"
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Stack } from "@/components/layout/stack"
import {
  useBulkArchive,
  useBulkAssignRecruiter,
  useBulkDeleteCandidates,
  useBulkReject,
  useBulkRestore,
  useBulkShortlist,
  useBulkUpdatePipelineStage,
  useOrgMembers,
} from "@/hooks"
import type { PipelineStage } from "@/types"

import { PIPELINE_STAGE_OPTIONS } from "./constants"

export interface CandidatesBulkActionBarProps {
  selectedIds: string[]
  onClear: () => void
  /** Show the Restore action — pass true only when every selected candidate
   * is currently in a terminal stage (REJECTED/WITHDRAWN/ARCHIVED). Kept as a
   * boolean prop so this bar stays dumb/reusable across the table and board. */
  showRestore?: boolean
}

function CandidatesBulkActionBar({ selectedIds, onClear, showRestore = false }: CandidatesBulkActionBarProps) {
  const [assignOpen, setAssignOpen] = React.useState(false)
  const [deleteOpen, setDeleteOpen] = React.useState(false)
  const [archiveOpen, setArchiveOpen] = React.useState(false)
  const [stageMoveOpen, setStageMoveOpen] = React.useState(false)
  const [recruiterId, setRecruiterId] = React.useState("")
  const [targetStage, setTargetStage] = React.useState<PipelineStage>("SHORTLISTED")

  const membersQuery = useOrgMembers()
  const bulkShortlist = useBulkShortlist()
  const bulkReject = useBulkReject()
  const bulkAssign = useBulkAssignRecruiter()
  const bulkDelete = useBulkDeleteCandidates()
  const bulkArchive = useBulkArchive()
  const bulkRestore = useBulkRestore()
  const bulkStageMove = useBulkUpdatePipelineStage()

  function reportResult(action: string, result: { succeeded: string[]; failed: { reason: string }[] }) {
    if (result.failed.length > 0) {
      toast.error(`${action}: ${result.succeeded.length} succeeded, ${result.failed.length} failed`)
    } else {
      toast.success(`${action}: ${result.succeeded.length} candidate(s)`)
    }
    onClear()
  }

  function handleBulkShortlist() {
    bulkShortlist.mutate(selectedIds, {
      onSuccess: (result) => reportResult("Shortlisted", result),
      onError: (error) => toast.error(error.message || "Bulk shortlist failed"),
    })
  }

  function handleBulkReject() {
    bulkReject.mutate(selectedIds, {
      onSuccess: (result) => reportResult("Rejected", result),
      onError: (error) => toast.error(error.message || "Bulk reject failed"),
    })
  }

  function handleBulkAssign() {
    bulkAssign.mutate(
      { resumeFileIds: selectedIds, recruiterId: recruiterId || null },
      {
        onSuccess: (result) => {
          reportResult("Assigned", result)
          setAssignOpen(false)
        },
        onError: (error) => toast.error(error.message || "Bulk assign failed"),
      }
    )
  }

  function handleBulkDelete() {
    bulkDelete.mutate(selectedIds, {
      onSuccess: (result) => {
        reportResult("Deleted", result)
        setDeleteOpen(false)
      },
      onError: (error) => toast.error(error.message || "Bulk delete failed"),
    })
  }

  function handleBulkArchive() {
    bulkArchive.mutate(selectedIds, {
      onSuccess: (result) => {
        reportResult("Archived", result)
        setArchiveOpen(false)
      },
      onError: (error) => toast.error(error.message || "Bulk archive failed"),
    })
  }

  function handleBulkRestore() {
    bulkRestore.mutate(selectedIds, {
      onSuccess: (result) => reportResult("Restored", result),
      onError: (error) => toast.error(error.message || "Bulk restore failed"),
    })
  }

  function handleBulkStageMove() {
    bulkStageMove.mutate(
      { resumeFileIds: selectedIds, pipelineStage: targetStage },
      {
        onSuccess: (result) => {
          reportResult("Moved", result)
          setStageMoveOpen(false)
        },
        onError: (error) => toast.error(error.message || "Bulk stage move failed"),
      }
    )
  }

  const isWorking =
    bulkShortlist.isPending ||
    bulkReject.isPending ||
    bulkAssign.isPending ||
    bulkDelete.isPending ||
    bulkArchive.isPending ||
    bulkRestore.isPending ||
    bulkStageMove.isPending

  return (
    <>
      <Stack
        direction="row"
        align="center"
        justify="between"
        gap="md"
        className="rounded-lg border border-border bg-muted/50 px-3 py-2"
      >
        <span className="text-sm text-foreground">{selectedIds.length} selected</span>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={handleBulkShortlist} disabled={isWorking}>
            Shortlist
          </Button>
          <Button variant="outline" size="sm" onClick={handleBulkReject} disabled={isWorking}>
            Reject
          </Button>
          <Button variant="outline" size="sm" onClick={() => setAssignOpen(true)} disabled={isWorking}>
            Assign Recruiter
          </Button>
          <Button variant="outline" size="sm" onClick={() => setStageMoveOpen(true)} disabled={isWorking}>
            Move Stage
          </Button>
          <Button variant="outline" size="sm" onClick={() => setArchiveOpen(true)} disabled={isWorking}>
            Archive
          </Button>
          {showRestore && (
            <Button variant="outline" size="sm" onClick={handleBulkRestore} disabled={isWorking}>
              Restore
            </Button>
          )}
          <Button variant="destructive" size="sm" onClick={() => setDeleteOpen(true)} disabled={isWorking}>
            Delete
          </Button>
        </div>
      </Stack>

      <Dialog open={assignOpen} onOpenChange={setAssignOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign recruiter</DialogTitle>
            <DialogDescription>Assign a recruiter to {selectedIds.length} selected candidate(s).</DialogDescription>
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
            <Button isLoading={bulkAssign.isPending} onClick={handleBulkAssign}>
              Assign
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete {selectedIds.length} candidate(s)?</DialogTitle>
            <DialogDescription>
              These applications will be removed from this campaign. This can be reversed by an administrator.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" isLoading={bulkDelete.isPending} onClick={handleBulkDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={archiveOpen} onOpenChange={setArchiveOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Archive {selectedIds.length} candidate(s)?</DialogTitle>
            <DialogDescription>
              Archived candidates are hidden from the active pipeline but can be restored later.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setArchiveOpen(false)}>
              Cancel
            </Button>
            <Button isLoading={bulkArchive.isPending} onClick={handleBulkArchive}>
              Archive
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={stageMoveOpen} onOpenChange={setStageMoveOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Move pipeline stage</DialogTitle>
            <DialogDescription>Move {selectedIds.length} selected candidate(s) to a new stage.</DialogDescription>
          </DialogHeader>
          <Select value={targetStage} onValueChange={(v) => setTargetStage(v as PipelineStage)}>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PIPELINE_STAGE_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <DialogFooter>
            <Button variant="outline" onClick={() => setStageMoveOpen(false)}>
              Cancel
            </Button>
            <Button isLoading={bulkStageMove.isPending} onClick={handleBulkStageMove}>
              Move
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

export { CandidatesBulkActionBar }
