import { CheckCircle2, TrendingUp } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { CommunicationAssessment } from "@/types"

export interface StrengthsImprovementsProps {
  communicationAssessment: CommunicationAssessment | null
}

function StrengthsImprovements({ communicationAssessment }: StrengthsImprovementsProps) {
  if (!communicationAssessment || communicationAssessment.status !== "COMPLETED") {
    return null
  }

  const strengths = communicationAssessment.strengths_json ?? []
  const improvements = communicationAssessment.improvements_json ?? []

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-success-emphasis">Strengths</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {strengths.length > 0 ? (
            strengths.map((strength) => (
              <Badge key={strength} variant="success" className="w-fit">
                <CheckCircle2 aria-hidden="true" />
                {strength}
              </Badge>
            ))
          ) : (
            <span className="text-sm text-muted-foreground">No notable strengths identified.</span>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-warning-emphasis">Improvement Areas</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {improvements.length > 0 ? (
            improvements.map((improvement) => (
              <Badge key={improvement} variant="warning" className="w-fit">
                <TrendingUp aria-hidden="true" />
                {improvement}
              </Badge>
            ))
          ) : (
            <span className="text-sm text-muted-foreground">No improvement areas identified.</span>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export { StrengthsImprovements }
