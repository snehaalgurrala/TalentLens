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
import { Textarea } from "@/components/ui/textarea"
import { useUpdateNotes } from "@/hooks"
import type { CandidateListItem } from "@/types"

export interface CandidateNotesDialogProps {
  candidate: CandidateListItem | null
  onOpenChange: (open: boolean) => void
}

function CandidateNotesDialog({ candidate, onOpenChange }: CandidateNotesDialogProps) {
  const [notes, setNotes] = React.useState("")
  const updateNotes = useUpdateNotes()

  React.useEffect(() => {
    setNotes(candidate?.notes ?? "")
  }, [candidate])

  function handleSave() {
    if (!candidate) return
    updateNotes.mutate(
      { resumeFileId: candidate.resume_file_id, notes: notes.trim() || null },
      {
        onSuccess: () => {
          toast.success("Notes saved")
          onOpenChange(false)
        },
        onError: (error) => toast.error(error.message || "Failed to save notes"),
      }
    )
  }

  return (
    <Dialog open={candidate !== null} onOpenChange={(open) => !open && onOpenChange(false)}>
      <DialogContent>
        {candidate && (
          <>
            <DialogHeader>
              <DialogTitle>Notes — {candidate.candidate_name}</DialogTitle>
              <DialogDescription>Visible to your team when reviewing this candidate.</DialogDescription>
            </DialogHeader>
            <Textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Add a note about this candidate..."
              rows={5}
              maxLength={5000}
              autoFocus
            />
            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button isLoading={updateNotes.isPending} onClick={handleSave}>
                Save
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

export { CandidateNotesDialog }
