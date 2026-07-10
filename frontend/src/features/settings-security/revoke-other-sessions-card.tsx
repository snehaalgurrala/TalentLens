"use client"

import * as React from "react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { useRevokeOtherSessions } from "@/hooks"

function RevokeOtherSessionsCard() {
  const [confirmOpen, setConfirmOpen] = React.useState(false)
  const revokeOtherSessions = useRevokeOtherSessions()

  async function handleConfirm() {
    try {
      await revokeOtherSessions.mutateAsync()
      toast.success("Signed out of all other sessions")
      setConfirmOpen(false)
    } catch (error) {
      const message = error instanceof Error ? error.message : "Something went wrong"
      toast.error(message)
    }
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Sign Out Other Sessions</CardTitle>
          <CardDescription>
            Immediately signs you out everywhere except this device.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="destructive" onClick={() => setConfirmOpen(true)}>
            Revoke Other Sessions
          </Button>
        </CardContent>
      </Card>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Revoke all other sessions?</DialogTitle>
            <DialogDescription>
              Every other device and browser signed in to your account will be signed out
              immediately. This can&apos;t be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              isLoading={revokeOtherSessions.isPending}
              onClick={() => void handleConfirm()}
            >
              Revoke Other Sessions
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

export { RevokeOtherSessionsCard }
