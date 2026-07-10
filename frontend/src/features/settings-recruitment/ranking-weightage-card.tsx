"use client"

import * as React from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { DashboardErrorState } from "@/features/dashboard"
import { useCreateScoringRule, useScoringRule, useUpdateScoringRule } from "@/hooks/use-scoring-rule"
import type { ScoringRule, ScoringRuleWeightsPayload } from "@/services/scoring-rule.service"
import { cn } from "@/lib/utils"

import {
  MAX_PREFERRED_COMPANY_BONUS,
  scoringWeightsFormSchema,
  WEIGHT_FIELD_KEYS,
  WEIGHT_SUM_TOLERANCE,
  type ScoringWeightsFormValues,
} from "./schemas"

const WEIGHT_FIELD_LABELS: Record<(typeof WEIGHT_FIELD_KEYS)[number], string> = {
  semantic_weight: "Semantic Match",
  skills_weight: "Skills Match",
  experience_weight: "Experience",
  education_weight: "Education",
  project_weight: "Projects",
  certification_weight: "Certifications",
}

const DEFAULT_WEIGHTS: Record<(typeof WEIGHT_FIELD_KEYS)[number], string> = {
  semantic_weight: "0.30",
  skills_weight: "0.25",
  experience_weight: "0.20",
  education_weight: "0.10",
  project_weight: "0.10",
  certification_weight: "0.05",
}

function ruleToFormValues(rule: ScoringRule | null): ScoringWeightsFormValues {
  if (!rule) {
    return { ...DEFAULT_WEIGHTS, preferred_company_bonus: "0.00" }
  }
  return {
    semantic_weight: rule.semantic_weight.toString(),
    skills_weight: rule.skills_weight.toString(),
    experience_weight: rule.experience_weight.toString(),
    education_weight: rule.education_weight.toString(),
    project_weight: rule.project_weight.toString(),
    certification_weight: rule.certification_weight.toString(),
    preferred_company_bonus: rule.preferred_company_bonus.toString(),
  }
}

function RankingWeightageCard() {
  const scoringRuleQuery = useScoringRule()
  const createScoringRule = useCreateScoringRule()
  const updateScoringRule = useUpdateScoringRule()

  const rule = scoringRuleQuery.data ?? null
  const isMissing = scoringRuleQuery.isError && scoringRuleQuery.error.status === 404

  const [preferredCompanies, setPreferredCompanies] = React.useState<string[]>([])
  const [newCompany, setNewCompany] = React.useState("")

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<ScoringWeightsFormValues>({
    resolver: zodResolver(scoringWeightsFormSchema),
    defaultValues: ruleToFormValues(rule),
  })

  React.useEffect(() => {
    reset(ruleToFormValues(rule))
    setPreferredCompanies(rule?.preferred_companies ?? [])
  }, [rule, reset])

  const watchedWeights = watch([...WEIGHT_FIELD_KEYS])
  const weightSum = React.useMemo(
    () => watchedWeights.reduce((total, value) => total + (Number(value) || 0), 0),
    [watchedWeights]
  )
  const isSumValid = Math.abs(weightSum - 1) < WEIGHT_SUM_TOLERANCE

  function addPreferredCompany() {
    const trimmed = newCompany.trim()
    if (!trimmed || preferredCompanies.includes(trimmed)) {
      setNewCompany("")
      return
    }
    setPreferredCompanies((prev) => [...prev, trimmed])
    setNewCompany("")
  }

  function removePreferredCompany(company: string) {
    setPreferredCompanies((prev) => prev.filter((item) => item !== company))
  }

  async function onSubmit(values: ScoringWeightsFormValues) {
    const payload: ScoringRuleWeightsPayload = {
      semantic_weight: Number(values.semantic_weight),
      skills_weight: Number(values.skills_weight),
      experience_weight: Number(values.experience_weight),
      education_weight: Number(values.education_weight),
      project_weight: Number(values.project_weight),
      certification_weight: Number(values.certification_weight),
      preferred_company_bonus: Number(values.preferred_company_bonus),
      preferred_companies: preferredCompanies,
    }

    try {
      if (rule) {
        await updateScoringRule.mutateAsync(payload)
      } else {
        await createScoringRule.mutateAsync(payload)
      }
      toast.success("Ranking weightage saved")
    } catch (error) {
      const message = error instanceof Error ? error.message : "Something went wrong"
      toast.error(message)
    }
  }

  if (scoringRuleQuery.isPending) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Ranking Weightage</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-64 w-full" />
        </CardContent>
      </Card>
    )
  }

  if (scoringRuleQuery.isError && !isMissing) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Ranking Weightage</CardTitle>
        </CardHeader>
        <CardContent>
          <DashboardErrorState
            error={scoringRuleQuery.error}
            onRetry={() => void scoringRuleQuery.refetch()}
          />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Ranking Weightage</CardTitle>
        <CardDescription>
          {isMissing
            ? "No default weighting is configured yet — set one to control how candidates are ranked."
            : "Controls how each signal contributes to a candidate's overall match score."}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form noValidate onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {WEIGHT_FIELD_KEYS.map((key) => (
              <div key={key} className="flex flex-col gap-1.5">
                <Label htmlFor={`weight-${key}`}>{WEIGHT_FIELD_LABELS[key]}</Label>
                <Input
                  id={`weight-${key}`}
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  aria-invalid={!!errors[key]}
                  {...register(key)}
                />
                {errors[key] && <p className="text-xs text-destructive">{errors[key]?.message}</p>}
              </div>
            ))}
          </div>

          <p
            className={cn(
              "text-sm font-medium",
              isSumValid ? "text-success-emphasis" : "text-destructive-emphasis"
            )}
          >
            Total: {weightSum.toFixed(2)} {isSumValid ? "(valid)" : "(must sum to 1.00)"}
          </p>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="preferred-company-bonus">
                Preferred Company Bonus (max {MAX_PREFERRED_COMPANY_BONUS})
              </Label>
              <Input
                id="preferred-company-bonus"
                type="number"
                step="0.01"
                min="0"
                max={MAX_PREFERRED_COMPANY_BONUS}
                aria-invalid={!!errors.preferred_company_bonus}
                {...register("preferred_company_bonus")}
              />
              {errors.preferred_company_bonus && (
                <p className="text-xs text-destructive">{errors.preferred_company_bonus.message}</p>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="preferred-company-input">Preferred Companies</Label>
            <div className="flex gap-2">
              <Input
                id="preferred-company-input"
                placeholder="Add a company name"
                value={newCompany}
                onChange={(event) => setNewCompany(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault()
                    addPreferredCompany()
                  }
                }}
              />
              <Button type="button" variant="outline" onClick={addPreferredCompany}>
                Add
              </Button>
            </div>
            {preferredCompanies.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {preferredCompanies.map((company) => (
                  <Badge key={company} variant="secondary" className="gap-1">
                    {company}
                    <button
                      type="button"
                      onClick={() => removePreferredCompany(company)}
                      aria-label={`Remove ${company}`}
                      className="ml-0.5 text-muted-foreground hover:text-destructive-emphasis"
                    >
                      ×
                    </button>
                  </Badge>
                ))}
              </div>
            )}
          </div>

          <div>
            <Button type="submit" isLoading={isSubmitting} disabled={!isSumValid}>
              Save Ranking Weightage
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

export { RankingWeightageCard }
