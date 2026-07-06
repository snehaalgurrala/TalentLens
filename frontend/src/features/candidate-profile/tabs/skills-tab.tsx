"use client"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { useCandidateMatchAnalysis } from "@/hooks"
import { categorizeSkill } from "@/features/candidate-profile/constants"

export interface SkillsTabProps {
  candidateId: string
  skills: string[]
}

function SkillsTab({ candidateId, skills }: SkillsTabProps) {
  const matchQuery = useCandidateMatchAnalysis(candidateId)
  const analysis = matchQuery.data

  const missingRequired = new Set(
    (analysis?.skills_details.required?.missing ?? []).map((s) => s.toLowerCase())
  )
  const matchedRequired = new Set(
    [
      ...(analysis?.skills_details.required?.exact_matches ?? []),
      ...(analysis?.skills_details.required?.synonym_matches ?? []).map((e) => e.matched_to),
      ...(analysis?.skills_details.required?.partial_matches ?? []).map((e) => e.matched_to),
    ].map((s) => s.toLowerCase())
  )

  if (skills.length === 0) {
    return (
      <TableEmptyState
        title="No skills parsed"
        description="This resume didn't include a recognizable skills section."
      />
    )
  }

  const grouped = new Map<string, string[]>()
  for (const skill of skills) {
    const category = categorizeSkill(skill)
    grouped.set(category, [...(grouped.get(category) ?? []), skill])
  }

  return (
    <div className="flex flex-col gap-4">
      {analysis && missingRequired.size > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-destructive-emphasis">Missing required skills</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-1.5">
            {[...missingRequired].map((skill) => (
              <Badge key={skill} variant="destructive">
                {skill}
              </Badge>
            ))}
          </CardContent>
        </Card>
      )}
      {[...grouped.entries()].map(([category, categorySkills]) => (
        <Card key={category}>
          <CardHeader>
            <CardTitle>{category}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-1.5">
            {categorySkills.map((skill) => {
              const matched = matchedRequired.has(skill.toLowerCase())
              return (
                <Badge key={skill} variant={matched ? "success" : "outline"}>
                  {skill}
                </Badge>
              )
            })}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export { SkillsTab }
