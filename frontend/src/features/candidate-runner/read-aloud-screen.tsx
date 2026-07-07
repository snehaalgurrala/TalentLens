"use client"

import { useRouter } from "next/navigation"

import { Container } from "@/components/layout/container"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAssessmentRunner } from "./assessment-runner-context"
import { AssessmentProgressHeader } from "./assessment-progress-header"
import { readAloudSentence } from "./mock-data"
import { RecordingCard } from "./recording-card"

function ReadAloudScreen() {
  const router = useRouter()
  const {
    section1Submitted,
    readAloudRecording,
    setReadAloudRecording,
    readAloudCompleted,
    listenRepeatCompleted,
    completeReadAloud,
  } = useAssessmentRunner()

  const handleContinue = () => {
    completeReadAloud()
    router.push("/assessment/listen-repeat")
  }

  return (
    <div className="flex min-h-dvh w-full flex-col bg-background">
      <AssessmentProgressHeader
        current="read-aloud"
        completed={{
          aptitude: section1Submitted,
          "read-aloud": readAloudCompleted,
          "listen-repeat": listenRepeatCompleted,
        }}
      />
      <Container size="md" className="flex flex-1 flex-col items-center justify-center gap-6 py-10">
        <Card className="w-full max-w-xl">
          <CardHeader className="items-center text-center">
            <CardTitle>Read Aloud</CardTitle>
            <CardDescription>
              Read the sentence below out loud, then record yourself reading it.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="rounded-lg bg-muted px-6 py-8 text-center text-h5 leading-snug text-foreground">
              {readAloudSentence}
            </p>
          </CardContent>
        </Card>
        <div className="w-full max-w-xl">
          <RecordingCard
            value={readAloudRecording}
            onChange={setReadAloudRecording}
            onContinue={handleContinue}
            continueLabel="Continue to Section 3"
          />
        </div>
      </Container>
    </div>
  )
}

export { ReadAloudScreen }
