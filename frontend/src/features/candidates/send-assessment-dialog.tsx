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
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Stack } from "@/components/layout/stack"
import { useSendAssessmentInvitations } from "@/hooks/use-assessment-invitations"
import type { AssessmentInvitationSendResult } from "@/types"

export interface SendAssessmentCandidate {
  candidateId: string
  name: string
}

export interface SendAssessmentDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  campaignId: string
  candidates: SendAssessmentCandidate[]
  /** Called once the recruiter dismisses the results view — parent should
   * clear its selection, matching every other bulk action's reportResult. */
  onDone: () => void
}

type ExpirationPreset = "24" | "48" | "72" | "custom"

const EXPIRATION_PRESETS: { value: ExpirationPreset; label: string }[] = [
  { value: "24", label: "24 hours" },
  { value: "48", label: "48 hours" },
  { value: "72", label: "72 hours" },
  { value: "custom", label: "Custom" },
]

const DEFAULT_CUSTOM_HOURS = "48"
const MIN_EXPIRATION_HOURS = 1
const MAX_EXPIRATION_HOURS = 24 * 90

function SendAssessmentDialog({
  open,
  onOpenChange,
  campaignId,
  candidates,
  onDone,
}: SendAssessmentDialogProps) {
  const [preset, setPreset] = React.useState<ExpirationPreset>("48")
  const [customHours, setCustomHours] = React.useState(DEFAULT_CUSTOM_HOURS)
  const [result, setResult] = React.useState<AssessmentInvitationSendResult | null>(null)
  const sendInvitations = useSendAssessmentInvitations()

  const expirationHours = preset === "custom" ? Number(customHours) : Number(preset)
  const isValidHours =
    Number.isFinite(expirationHours) &&
    expirationHours >= MIN_EXPIRATION_HOURS &&
    expirationHours <= MAX_EXPIRATION_HOURS

  const nameByCandidateId = React.useMemo(
    () => new Map(candidates.map((c) => [c.candidateId, c.name])),
    [candidates]
  )

  function resetForm() {
    setPreset("48")
    setCustomHours(DEFAULT_CUSTOM_HOURS)
    setResult(null)
  }

  function handleOpenChange(next: boolean) {
    if (!next) resetForm()
    onOpenChange(next)
  }

  function handleSend() {
    sendInvitations.mutate(
      {
        campaign_id: campaignId,
        candidate_ids: candidates.map((c) => c.candidateId),
        expiration_hours: expirationHours,
      },
      {
        onSuccess: (sendResult) => {
          setResult(sendResult)
          if (sendResult.failed.length > 0) {
            toast.error(`${sendResult.succeeded.length} sent, ${sendResult.failed.length} failed`)
          } else {
            toast.success(`Sent ${sendResult.succeeded.length} assessment invitation(s)`)
          }
        },
        onError: (error) => toast.error(error.message || "Failed to send assessment invitations"),
      }
    )
  }

  function handleDone() {
    onDone()
    handleOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        {result ? (
          <>
            <DialogHeader>
              <DialogTitle>Assessment Invitations Sent</DialogTitle>
              <DialogDescription>
                {result.succeeded.length} succeeded, {result.failed.length} failed.
              </DialogDescription>
            </DialogHeader>
            {result.failed.length > 0 && (
              <Stack
                gap="xs"
                className="max-h-64 overflow-y-auto rounded-lg border border-border p-2"
              >
                {result.failed.map((failure) => (
                  <div key={failure.candidate_id} className="flex flex-col gap-0.5 px-2 py-1.5 text-sm">
                    <span className="font-medium text-foreground">
                      {nameByCandidateId.get(failure.candidate_id) ?? "Unknown candidate"}
                    </span>
                    <span className="text-caption text-destructive">{failure.reason}</span>
                  </div>
                ))}
              </Stack>
            )}
            <DialogFooter>
              <Button onClick={handleDone}>Done</Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Send Assessment</DialogTitle>
              <DialogDescription>
                Email an assessment invitation to {candidates.length} selected candidate(s).
              </DialogDescription>
            </DialogHeader>
            <Stack gap="md">
              <RadioGroup
                value={preset}
                onValueChange={(value) => setPreset(value as ExpirationPreset)}
              >
                {EXPIRATION_PRESETS.map((option) => (
                  <div key={option.value} className="flex items-center gap-2.5">
                    <RadioGroupItem value={option.value} id={`expiration-${option.value}`} />
                    <Label htmlFor={`expiration-${option.value}`} className="cursor-pointer font-normal">
                      {option.label}
                    </Label>
                  </div>
                ))}
              </RadioGroup>
              {preset === "custom" && (
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="custom-expiration-hours">Expiration (hours)</Label>
                  <Input
                    id="custom-expiration-hours"
                    type="number"
                    min={MIN_EXPIRATION_HOURS}
                    max={MAX_EXPIRATION_HOURS}
                    value={customHours}
                    onChange={(event) => setCustomHours(event.target.value)}
                  />
                </div>
              )}
            </Stack>
            <DialogFooter>
              <Button variant="outline" onClick={() => handleOpenChange(false)}>
                Cancel
              </Button>
              <Button
                isLoading={sendInvitations.isPending}
                disabled={!isValidHours || candidates.length === 0}
                onClick={handleSend}
              >
                Send Assessment
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

export { SendAssessmentDialog }
