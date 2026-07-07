"use client"

import * as React from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Clock } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useCreateOrResumeSession } from "@/hooks/use-assessment-session"
import { useAssessmentRunner } from "./assessment-runner-context"
import { assessmentMeta } from "./mock-data"
import { AssessmentScreenShell } from "./assessment-screen-shell"

function LandingScreen() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { sessionId, setSessionId } = useAssessmentRunner()
  const createSession = useCreateOrResumeSession()
  const hasRequestedRef = React.useRef(false)

  const campaignId = searchParams.get("campaign_id")
  const candidateId = searchParams.get("candidate_id")
  const hasValidLink = Boolean(campaignId && candidateId)

  React.useEffect(() => {
    if (!hasValidLink || hasRequestedRef.current || sessionId) return
    hasRequestedRef.current = true
    createSession.mutate(
      { campaign_id: campaignId as string, candidate_id: candidateId as string },
      { onSuccess: (session) => setSessionId(session.id) }
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasValidLink, campaignId, candidateId, sessionId])

  if (!hasValidLink) {
    return (
      <AssessmentScreenShell>
        <Card>
          <CardHeader className="items-center text-center">
            <CardTitle className="text-h5">Invalid Assessment Link</CardTitle>
            <CardDescription>
              This assessment link is invalid or incomplete. Please use the link provided in your
              invitation email.
            </CardDescription>
          </CardHeader>
        </Card>
      </AssessmentScreenShell>
    )
  }

  return (
    <AssessmentScreenShell>
      <Card>
        <CardHeader className="items-center text-center">
          <CardTitle className="text-h5">{assessmentMeta.title}</CardTitle>
          <CardDescription>Invitation from {assessmentMeta.companyName}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-6 text-center">
          <div className="flex items-center gap-1.5 text-caption text-muted-foreground">
            <Clock className="size-3.5" aria-hidden="true" />
            Estimated time: ~{assessmentMeta.estimatedMinutes} minutes
          </div>
          <p className="text-sm text-muted-foreground">
            You&apos;ve been invited to complete a short assessment consisting of aptitude
            questions and two brief speaking exercises. Once you begin, please complete it in one
            sitting.
          </p>
          <Button
            size="lg"
            className="w-full"
            isLoading={createSession.isPending}
            disabled={!sessionId}
            onClick={() => router.push("/assessment/device-check")}
          >
            Begin Assessment
          </Button>
        </CardContent>
      </Card>
    </AssessmentScreenShell>
  )
}

export { LandingScreen }
