"use client"

import * as React from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { toast } from "sonner"
import { z } from "zod"

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
import { useCurrentUser } from "@/hooks"
import { organizationService } from "@/services/organization.service"
import type { ApiError } from "@/types"

const inviteFormSchema = z.object({
  email: z.string().min(1, "Email is required").email("Enter a valid email address"),
})

type InviteFormValues = z.infer<typeof inviteFormSchema>

export interface InviteUserDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onInvited: () => void
}

function InviteUserDialog({ open, onOpenChange, onInvited }: InviteUserDialogProps) {
  const { user } = useCurrentUser()
  const [invitedToken, setInvitedToken] = React.useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<InviteFormValues>({
    resolver: zodResolver(inviteFormSchema),
    defaultValues: { email: "" },
  })

  React.useEffect(() => {
    if (open) {
      reset({ email: "" })
      setInvitedToken(null)
    }
  }, [open, reset])

  async function onSubmit(values: InviteFormValues) {
    if (!user?.org_id) {
      toast.error("Your account isn't linked to an organization")
      return
    }
    try {
      const invitation = await organizationService.inviteRecruiter(user.org_id, { email: values.email.trim() })
      toast.success(`Invitation sent to ${values.email}`)
      setInvitedToken(invitation.token)
      onInvited()
    } catch (error) {
      const apiError = error as ApiError
      toast.error(apiError.message || "Failed to send invitation")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {invitedToken ? (
          <>
            <DialogHeader>
              <DialogTitle>Invitation sent</DialogTitle>
              <DialogDescription>
                An invitation email has been sent. The invite token is also shown below in case you need
                to share it directly.
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="invite-token">Invite Token</Label>
              <div className="flex gap-2">
                <Input id="invite-token" readOnly value={invitedToken} className="font-mono text-xs" />
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    void navigator.clipboard.writeText(invitedToken)
                    toast.success("Token copied to clipboard")
                  }}
                >
                  Copy
                </Button>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" onClick={() => onOpenChange(false)}>
                Done
              </Button>
            </DialogFooter>
          </>
        ) : (
          <form noValidate onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
            <DialogHeader>
              <DialogTitle>Invite User</DialogTitle>
              <DialogDescription>
                Send an invitation email. New invitees join your organization as a Recruiter.
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="invite-email">Email</Label>
              <Input
                id="invite-email"
                type="email"
                aria-invalid={!!errors.email}
                {...register("email")}
              />
              {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" isLoading={isSubmitting}>
                Send Invitation
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}

export { InviteUserDialog }
