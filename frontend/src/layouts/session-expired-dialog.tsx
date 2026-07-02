"use client"

import * as React from "react"
import { useRouter, useSearchParams } from "next/navigation"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

/** Shown on the login page after the interceptor force-logs-out an expired session. */
function SessionExpiredDialog() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [open, setOpen] = React.useState(searchParams.get("session_expired") === "1")

  function handleOpenChange(next: boolean) {
    setOpen(next)
    if (!next) {
      router.replace("/login")
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Session expired</DialogTitle>
          <DialogDescription>
            You&apos;ve been signed out for your security. Please log in again to continue.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button onClick={() => handleOpenChange(false)}>Okay</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export { SessionExpiredDialog }
