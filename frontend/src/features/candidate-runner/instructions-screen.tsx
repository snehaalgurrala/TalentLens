"use client"

import { useRouter } from "next/navigation"
import { AlertTriangle, ListChecks, Mic2, Speech } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { AssessmentScreenShell } from "./assessment-screen-shell"

const SECTIONS = [
  {
    icon: ListChecks,
    title: "Section 1 — Aptitude",
    description: "5 multiple-choice questions. Answer each, then review before submitting.",
  },
  {
    icon: Speech,
    title: "Section 2 — Read Aloud",
    description: "Read one sentence out loud and record yourself reading it.",
  },
  {
    icon: Mic2,
    title: "Section 3 — Listen & Repeat",
    description: "Listen to a sentence once, then record yourself repeating it.",
  },
]

function InstructionsScreen() {
  const router = useRouter()

  return (
    <AssessmentScreenShell maxWidthClassName="max-w-xl">
      <Card>
        <CardHeader>
          <CardTitle>Before You Begin</CardTitle>
          <CardDescription>Here&apos;s what to expect across the three sections.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          <div className="flex flex-col gap-3">
            {SECTIONS.map((section) => (
              <div key={section.title} className="flex items-start gap-3 rounded-lg border border-border px-4 py-3">
                <section.icon className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
                <div className="flex flex-col gap-0.5">
                  <span className="text-sm font-medium text-foreground">{section.title}</span>
                  <span className="text-caption text-muted-foreground">{section.description}</span>
                </div>
              </div>
            ))}
          </div>
          <div className="flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/10 px-4 py-3 text-caption text-warning-emphasis">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            Once you begin, you cannot pause or restart the assessment. You have one attempt, so
            please complete it in a quiet place with a stable connection.
          </div>
          <Button size="lg" className="w-full" onClick={() => router.push("/assessment/aptitude/1")}>
            Continue
          </Button>
        </CardContent>
      </Card>
    </AssessmentScreenShell>
  )
}

export { InstructionsScreen }
