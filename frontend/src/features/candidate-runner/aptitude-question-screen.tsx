"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { ArrowLeft, ArrowRight } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Container } from "@/components/layout/container"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { cn } from "@/lib/utils"
import { useAssessmentRunner } from "./assessment-runner-context"
import { AssessmentProgressHeader } from "./assessment-progress-header"
import { aptitudeQuestions } from "./mock-data"
import { Timer } from "./timer"

export interface AptitudeQuestionScreenProps {
  questionId: number
}

function AptitudeQuestionScreen({ questionId }: AptitudeQuestionScreenProps) {
  const router = useRouter()
  const {
    answers,
    setAnswer,
    section1Submitted,
    section1DeadlineAt,
    ensureSection1Timer,
    readAloudCompleted,
    listenRepeatCompleted,
  } = useAssessmentRunner()

  React.useEffect(() => {
    ensureSection1Timer()
  }, [ensureSection1Timer])

  const totalQuestions = aptitudeQuestions.length
  const question = aptitudeQuestions.find((q) => q.id === questionId)

  if (!question) {
    return null
  }

  const currentAnswer = answers[question.id]

  const goBack = () => {
    if (questionId > 1) router.push(`/assessment/aptitude/${questionId - 1}`)
  }

  const goNext = () => {
    if (questionId < totalQuestions) {
      router.push(`/assessment/aptitude/${questionId + 1}`)
    } else {
      router.push("/assessment/aptitude/review")
    }
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
      <Container size="md" className="flex flex-1 flex-col items-center justify-center gap-4 py-10">
        <div className="flex w-full max-w-xl items-center justify-between">
          <span className="text-caption font-medium text-muted-foreground">
            Question {questionId} of {totalQuestions}
          </span>
          {section1DeadlineAt && <Timer deadlineAt={section1DeadlineAt} />}
        </div>
        <div className="flex w-full max-w-xl gap-1.5" aria-hidden="true">
          {aptitudeQuestions.map((q) => (
            <span
              key={q.id}
              className={cn(
                "h-1.5 flex-1 rounded-full",
                q.id < questionId || (q.id === questionId && Boolean(currentAnswer))
                  ? "bg-primary"
                  : q.id === questionId
                    ? "bg-primary/40"
                    : "bg-muted"
              )}
            />
          ))}
        </div>

        <Card className="w-full max-w-xl">
          <CardHeader>
            <CardTitle className="text-h6">{question.prompt}</CardTitle>
          </CardHeader>
          <CardContent>
            <RadioGroup
              value={currentAnswer ?? ""}
              onValueChange={(value) => setAnswer(question.id, value)}
            >
              {question.options.map((option) => (
                <div
                  key={option.id}
                  className="flex items-center gap-2.5 rounded-lg border border-border px-3.5 py-2.5"
                >
                  <RadioGroupItem value={option.id} id={`q${question.id}-${option.id}`} />
                  <Label htmlFor={`q${question.id}-${option.id}`} className="flex-1 cursor-pointer font-normal">
                    {option.label}
                  </Label>
                </div>
              ))}
            </RadioGroup>
          </CardContent>
        </Card>

        <div className="flex w-full max-w-xl items-center justify-between">
          <Button variant="outline" onClick={goBack} disabled={questionId === 1}>
            <ArrowLeft /> Back
          </Button>
          <Button onClick={goNext} disabled={!currentAnswer}>
            {questionId < totalQuestions ? "Next" : "Review"} <ArrowRight />
          </Button>
        </div>
      </Container>
    </div>
  )
}

export { AptitudeQuestionScreen }
