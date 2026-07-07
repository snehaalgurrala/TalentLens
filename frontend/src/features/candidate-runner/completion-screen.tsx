"use client"

import { useRouter } from "next/navigation"
import { CheckCircle2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAssessmentRunner } from "./assessment-runner-context"
import { AssessmentScreenShell } from "./assessment-screen-shell"

function CompletionScreen() {
  const router = useRouter()
  const { resetAssessment } = useAssessmentRunner()

  const handleReturnHome = () => {
    resetAssessment()
    router.push("/")
  }

  return (
    <AssessmentScreenShell>
      <Card>
        <CardHeader className="items-center text-center">
          <div className="flex size-14 items-center justify-center rounded-full bg-success/10">
            <CheckCircle2 className="size-8 text-success" aria-hidden="true" />
          </div>
          <CardTitle className="mt-2">Assessment Submitted</CardTitle>
          <CardDescription>Thank you for completing the assessment.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-6 text-center">
          <p className="text-sm text-muted-foreground">
            The recruiter will review your assessment and reach out with next steps. You may now
            close this page.
          </p>
          <Button size="lg" className="w-full" onClick={handleReturnHome}>
            Return Home
          </Button>
        </CardContent>
      </Card>
    </AssessmentScreenShell>
  )
}

export { CompletionScreen }
