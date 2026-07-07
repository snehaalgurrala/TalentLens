"use client"

import { useRouter } from "next/navigation"
import { Pencil } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Container } from "@/components/layout/container"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAssessmentRunner } from "./assessment-runner-context"
import { AssessmentProgressHeader } from "./assessment-progress-header"
import { aptitudeQuestions } from "./mock-data"

function AptitudeReviewScreen() {
  const router = useRouter()
  const { answers, submitSection1, section1Submitted, readAloudCompleted, listenRepeatCompleted } =
    useAssessmentRunner()

  const handleSubmit = () => {
    submitSection1()
    router.push("/assessment/read-aloud")
  }

  return (
    <div className="flex min-h-dvh w-full flex-col bg-background">
      <AssessmentProgressHeader
        current="aptitude"
        completed={{
          aptitude: section1Submitted,
          "read-aloud": readAloudCompleted,
          "listen-repeat": listenRepeatCompleted,
        }}
      />
      <Container size="md" className="flex flex-1 justify-center py-10">
        <Card className="w-full max-w-xl">
          <CardHeader>
            <CardTitle>Review Your Answers</CardTitle>
            <CardDescription>
              Check your answers below. You can edit any question before submitting.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {aptitudeQuestions.map((question) => {
              const answerId = answers[question.id]
              const answerLabel = question.options.find((option) => option.id === answerId)?.label
              return (
                <div
                  key={question.id}
                  className="flex items-start justify-between gap-3 rounded-lg border border-border px-4 py-3"
                >
                  <div className="flex flex-col gap-1">
                    <span className="text-caption text-muted-foreground">
                      Question {question.id}
                    </span>
                    <span className="text-sm font-medium text-foreground">{question.prompt}</span>
                    <span className="text-sm text-primary">
                      {answerLabel ?? "Not answered"}
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => router.push(`/assessment/aptitude/${question.id}`)}
                  >
                    <Pencil /> Edit
                  </Button>
                </div>
              )
            })}
            <Button size="lg" className="mt-2 w-full" onClick={handleSubmit}>
              Submit Section 1
            </Button>
          </CardContent>
        </Card>
      </Container>
    </div>
  )
}

export { AptitudeReviewScreen }
