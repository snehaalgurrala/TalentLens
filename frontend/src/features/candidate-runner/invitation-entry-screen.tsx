"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { Loader2, WifiOff, XCircle } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useInvitationByToken } from "@/hooks/use-assessment-invitations"
import type { ApiError } from "@/types"
import { useAssessmentRunner } from "./assessment-runner-context"
import { AssessmentScreenShell } from "./assessment-screen-shell"

export interface InvitationEntryScreenProps {
  token: string
}

interface ErrorView {
  title: string
  description: string
}

function resolveErrorView(error: ApiError): ErrorView {
  const message = error.message.toLowerCase()

  if (error.status === 404) {
    return {
      title: "Invalid Assessment Link",
      description:
        "This assessment link is invalid. Please use the link provided in your invitation email.",
    }
  }
  if (error.status === 410) {
    if (message.includes("revoked")) {
      return {
        title: "Invitation Revoked",
        description:
          "This assessment invitation has been revoked. Please contact your recruiter for a new one.",
      }
    }
    if (message.includes("completed")) {
      return {
        title: "Assessment Already Completed",
        description: "You've already submitted this assessment. There's nothing more to do here.",
      }
    }
    return {
      title: "Assessment Link Expired",
      description:
        "This assessment link has expired. Please contact your recruiter to request a new invitation.",
    }
  }
  return {
    title: "Something Went Wrong",
    description:
      error.message || "We couldn't validate your assessment link. Please try again.",
  }
}

function InvitationEntryScreen({ token }: InvitationEntryScreenProps) {
  const router = useRouter()
  const { setSessionId, setInvitationToken } = useAssessmentRunner()
  const invitationQuery = useInvitationByToken(token)
  const navigatedRef = React.useRef(false)

  React.useEffect(() => {
    if (!invitationQuery.data || navigatedRef.current) return
    navigatedRef.current = true
    setSessionId(invitationQuery.data.assessment_session.id)
    setInvitationToken(token)
    router.replace("/assessment/device-check")
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [invitationQuery.data, token])

  if (invitationQuery.isError) {
    const isNetworkError = invitationQuery.error.status === 0
    const view = resolveErrorView(invitationQuery.error)

    return (
      <AssessmentScreenShell>
        <Card>
          <CardHeader className="items-center text-center">
            {isNetworkError ? (
              <WifiOff className="size-8 text-muted-foreground" aria-hidden="true" />
            ) : (
              <XCircle className="size-8 text-destructive" aria-hidden="true" />
            )}
            <CardTitle className="text-h5">{view.title}</CardTitle>
            <CardDescription>{view.description}</CardDescription>
          </CardHeader>
          {isNetworkError && (
            <CardContent className="flex justify-center">
              <Button variant="outline" onClick={() => invitationQuery.refetch()}>
                Try Again
              </Button>
            </CardContent>
          )}
        </Card>
      </AssessmentScreenShell>
    )
  }

  return (
    <AssessmentScreenShell>
      <Card>
        <CardHeader className="items-center text-center">
          <Loader2 className="size-8 animate-spin text-primary" aria-hidden="true" />
          <CardTitle className="text-h5">Validating Your Invitation</CardTitle>
          <CardDescription>
            Please wait a moment while we confirm your assessment link.
          </CardDescription>
        </CardHeader>
      </Card>
    </AssessmentScreenShell>
  )
}

export { InvitationEntryScreen }
