"use client"

import { PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer, Tooltip } from "recharts"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { Stack } from "@/components/layout/stack"
import { DashboardErrorState } from "@/features/dashboard"
import { RecommendationBadge } from "@/features/candidates/candidate-badges"
import { useCandidateMatchAnalysis } from "@/hooks"
import { useChartTheme } from "@/design-system/charts/useChartTheme"
import { cn } from "@/lib/utils"
import type { MatchSentiment } from "@/types"

export interface AiMatchTabProps {
  candidateId: string
}

const SENTIMENT_STYLE: Record<MatchSentiment, string> = {
  positive: "text-success-emphasis",
  negative: "text-destructive-emphasis",
  neutral: "text-muted-foreground",
}

const SUB_SCORE_LABELS: [key: string, label: string][] = [
  ["semantic_score", "Semantic"],
  ["skills_score", "Skills"],
  ["experience_score", "Experience"],
  ["education_score", "Education"],
  ["projects_score", "Projects"],
  ["certification_score", "Certifications"],
]

function AiMatchTab({ candidateId }: AiMatchTabProps) {
  const query = useCandidateMatchAnalysis(candidateId)
  const { palette, defaults } = useChartTheme()

  if (query.isPending) {
    return (
      <Stack gap="md">
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-64 w-full" />
      </Stack>
    )
  }

  if (query.isError) {
    if (query.error.status === 422) {
      return (
        <Card>
          <CardContent className="text-sm text-muted-foreground">
            {query.error.message ||
              "This candidate hasn't been ranked yet — the job description or resume may still be parsing/embedding."}
          </CardContent>
        </Card>
      )
    }
    return <DashboardErrorState error={query.error} onRetry={() => query.refetch()} />
  }

  const analysis = query.data
  const radarData = SUB_SCORE_LABELS.map(([key, label]) => ({
    label,
    value: analysis.sub_scores[key as keyof typeof analysis.sub_scores],
  }))

  const requiredSkills = analysis.skills_details.required
  const preferredSkills = analysis.skills_details.preferred

  return (
    <Stack gap="lg">
      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="text-h3 font-semibold tabular-nums text-foreground">
              {analysis.overall_score}%
            </span>
            <RecommendationBadge recommendation={analysis.recommendation} />
          </div>
          {analysis.preferred_company_matched && (
            <Badge variant="success">+{analysis.bonus_points.toFixed(0)} preferred-employer bonus</Badge>
          )}
        </CardContent>
      </Card>

      <p className="text-sm text-foreground">{analysis.match_explanation}</p>

      <Card>
        <CardHeader>
          <CardTitle>Score Breakdown</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <ResponsiveContainer width="100%" height={260}>
            <RadarChart data={radarData} outerRadius="75%">
              <PolarGrid stroke={defaults.grid.stroke} />
              <PolarAngleAxis
                dataKey="label"
                tick={{ fontSize: defaults.axis.fontSize, fill: defaults.axis.stroke }}
              />
              <Radar
                name="Candidate"
                dataKey="value"
                stroke={palette[0]}
                fill={palette[0]}
                fillOpacity={0.25}
              />
              <Tooltip contentStyle={defaults.tooltip.contentStyle} labelStyle={defaults.tooltip.labelStyle} />
            </RadarChart>
          </ResponsiveContainer>
          <div className="flex flex-col justify-center gap-3">
            {radarData.map(({ label, value }) => (
              <div key={label} className="flex flex-col gap-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-foreground">{label}</span>
                  <span className="font-semibold tabular-nums text-foreground">{value}%</span>
                </div>
                <Progress value={value} className="h-1.5" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Skills Comparison</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div>
            <p className="mb-1.5 text-caption font-medium text-muted-foreground">Matched (required)</p>
            <div className="flex flex-wrap gap-1.5">
              {requiredSkills?.exact_matches?.map((skill) => (
                <Badge key={skill} variant="success">
                  {skill}
                </Badge>
              ))}
              {requiredSkills?.synonym_matches?.map((entry) => (
                <Badge key={entry.skill} variant="success">
                  {entry.skill}
                </Badge>
              ))}
              {requiredSkills?.partial_matches?.map((entry) => (
                <Badge key={entry.skill} variant="pending">
                  {entry.skill}
                </Badge>
              ))}
              {!requiredSkills?.exact_matches?.length &&
                !requiredSkills?.synonym_matches?.length &&
                !requiredSkills?.partial_matches?.length && (
                  <span className="text-sm text-muted-foreground">—</span>
                )}
            </div>
          </div>
          <div>
            <p className="mb-1.5 text-caption font-medium text-muted-foreground">Missing (required)</p>
            <div className="flex flex-wrap gap-1.5">
              {requiredSkills?.missing?.length ? (
                requiredSkills.missing.map((skill) => (
                  <Badge key={skill} variant="destructive">
                    {skill}
                  </Badge>
                ))
              ) : (
                <span className="text-sm text-muted-foreground">None</span>
              )}
            </div>
          </div>
          {preferredSkills && (preferredSkills.exact_matches?.length || preferredSkills.missing?.length) ? (
            <div>
              <p className="mb-1.5 text-caption font-medium text-muted-foreground">Preferred skills</p>
              <div className="flex flex-wrap gap-1.5">
                {preferredSkills.exact_matches?.map((skill) => (
                  <Badge key={skill} variant="success">
                    {skill}
                  </Badge>
                ))}
                {preferredSkills.missing?.map((skill) => (
                  <Badge key={skill} variant="outline">
                    {skill}
                  </Badge>
                ))}
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {analysis.strengths.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-success-emphasis">Strengths</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="list-inside list-disc text-sm text-foreground">
                {analysis.strengths.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}
        {analysis.weaknesses.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-destructive-emphasis">Weaknesses</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="list-inside list-disc text-sm text-foreground">
                {analysis.weaknesses.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Explainable AI</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="flex flex-col gap-2">
            {analysis.explanation_items.map((item, i) => (
              <li key={i} className={cn("text-sm", SENTIMENT_STYLE[item.sentiment])}>
                {item.text}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </Stack>
  )
}

export { AiMatchTab }
