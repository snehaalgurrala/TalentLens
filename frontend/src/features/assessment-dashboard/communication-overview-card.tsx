import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import type { CommunicationAssessment } from "@/types"

import { scoreTone } from "./format"

export interface CommunicationOverviewCardProps {
  communicationAssessment: CommunicationAssessment | null
}

const SCORE_FIELDS: [key: "overall_score" | "reading_score" | "listening_score" | "confidence_score", label: string][] = [
  ["overall_score", "Overall Score"],
  ["reading_score", "Reading Score"],
  ["listening_score", "Listening Score"],
  ["confidence_score", "Confidence Score"],
]

function CommunicationOverviewCard({ communicationAssessment }: CommunicationOverviewCardProps) {
  if (!communicationAssessment || communicationAssessment.status !== "COMPLETED") {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Communication Overview</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {communicationAssessment?.status === "FAILED"
            ? (communicationAssessment.error_message ?? "Communication assessment failed to generate.")
            : "Communication scores appear once both Read Aloud and Listen & Repeat analyses finish processing."}
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Communication Overview</CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {SCORE_FIELDS.map(([key, label]) => {
          const value = communicationAssessment[key]
          if (value === null) return null
          return (
            <div key={key} className="flex flex-col gap-2">
              <span className="text-caption text-muted-foreground">{label}</span>
              <span className={`text-h6 font-semibold tabular-nums ${scoreTone(value)}`}>{value}%</span>
              <Progress value={value} className="h-1.5" />
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}

export { CommunicationOverviewCard }
