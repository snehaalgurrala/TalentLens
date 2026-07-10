"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { CheckCircle2, Volume2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Container } from "@/components/layout/container"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAssessmentRunner } from "./assessment-runner-context"
import { AssessmentProgressHeader } from "./assessment-progress-header"
import { RecordingCard } from "./recording-card"
import { listenRepeatSentence } from "./mock-data"

function ListenRepeatScreen() {
  const router = useRouter()
  const {
    section1Submitted,
    readAloudCompleted,
    listenRepeatRecording,
    setListenRepeatRecording,
    listenRepeatCompleted,
    completeListenRepeat,
  } = useAssessmentRunner()
  const [isPlaying, setIsPlaying] = React.useState(false)
  const [hasPlayed, setHasPlayed] = React.useState(false)
  const [speechSupported] = React.useState(
    () => typeof window !== "undefined" && Boolean(window.speechSynthesis)
  )

  // Stop any in-flight utterance if the candidate navigates away mid-speech.
  React.useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.cancel()
      }
    }
  }, [])

  const handlePlay = () => {
    if (!speechSupported || isPlaying || hasPlayed) return
    setIsPlaying(true)
    const utterance = new SpeechSynthesisUtterance(listenRepeatSentence)
    utterance.onend = () => {
      setIsPlaying(false)
      setHasPlayed(true)
    }
    utterance.onerror = () => {
      setIsPlaying(false)
      setHasPlayed(true)
    }
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(utterance)
  }

  const handleContinue = () => {
    completeListenRepeat()
    router.push("/assessment/uploading")
  }

  return (
    <div className="flex min-h-dvh w-full flex-col bg-background">
      <AssessmentProgressHeader
        current="listen-repeat"
        completed={{
          aptitude: section1Submitted,
          "read-aloud": readAloudCompleted,
          "listen-repeat": listenRepeatCompleted,
        }}
      />
      <Container size="md" className="flex flex-1 flex-col items-center justify-center gap-6 py-10">
        <Card className="w-full max-w-xl">
          <CardHeader className="items-center text-center">
            <CardTitle>Listen &amp; Repeat</CardTitle>
            <CardDescription>
              {speechSupported
                ? "Listen to the sentence once, then record yourself repeating it. You can only listen once, so pay close attention."
                : "Your browser can't play the sentence aloud, so it's shown below instead. Read it, then record yourself repeating it."}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center gap-4 py-4">
            {!speechSupported ? (
              <p className="rounded-md bg-muted px-4 py-3 text-center text-sm font-medium">
                {listenRepeatSentence}
              </p>
            ) : isPlaying ? (
              <div
                className="flex h-16 items-center justify-center gap-1"
                role="status"
                aria-live="polite"
              >
                <span className="sr-only">Playing sentence…</span>
                {Array.from({ length: 16 }).map((_, index) => (
                  <span
                    key={index}
                    className="w-1 animate-pulse rounded-full bg-primary"
                    style={{
                      height: `${30 + ((index * 37) % 70)}%`,
                      animationDelay: `${index * 60}ms`,
                    }}
                  />
                ))}
              </div>
            ) : (
              <div className="flex size-16 items-center justify-center rounded-full bg-muted">
                <Volume2 className="size-7 text-muted-foreground" aria-hidden="true" />
              </div>
            )}
            {speechSupported ? (
              <Button
                onClick={handlePlay}
                disabled={hasPlayed || isPlaying}
                size="lg"
                variant={hasPlayed ? "outline" : "default"}
              >
                {hasPlayed ? (
                  <>
                    <CheckCircle2 /> Played
                  </>
                ) : isPlaying ? (
                  "Playing…"
                ) : (
                  <>
                    <Volume2 /> Play Sentence
                  </>
                )}
              </Button>
            ) : (
              <Button
                onClick={() => setHasPlayed(true)}
                disabled={hasPlayed}
                size="lg"
                variant={hasPlayed ? "outline" : "default"}
              >
                {hasPlayed ? (
                  <>
                    <CheckCircle2 /> Ready
                  </>
                ) : (
                  "I've read the sentence"
                )}
              </Button>
            )}
          </CardContent>
        </Card>
        <div className="w-full max-w-xl">
          <RecordingCard
            value={listenRepeatRecording}
            onChange={setListenRepeatRecording}
            disabled={!hasPlayed}
            disabledReason="Listen to the sentence first to enable recording."
            onContinue={handleContinue}
            continueLabel="Finish Assessment"
          />
        </div>
      </Container>
    </div>
  )
}

export { ListenRepeatScreen }
