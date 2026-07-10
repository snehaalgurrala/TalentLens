"use client"

import * as React from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { Controller, useForm } from "react-hook-form"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { useUpdateRecruitmentSettings } from "@/hooks"
import type { RecruitmentSettings } from "@/types"

import { recruitmentPolicyFormSchema, type RecruitmentPolicyFormValues } from "./schemas"

export interface ResumePolicyCardProps {
  settings: RecruitmentSettings
}

const RESUME_FORMAT_OPTIONS = [
  { value: "pdf", label: "PDF" },
  { value: "doc", label: "DOC" },
  { value: "docx", label: "DOCX" },
]

function settingsToFormValues(settings: RecruitmentSettings): RecruitmentPolicyFormValues {
  return {
    default_resume_score_threshold: settings.default_resume_score_threshold.toString(),
    enable_explainable_ai: settings.enable_explainable_ai,
    max_resume_upload_count: settings.max_resume_upload_count.toString(),
    max_resume_size_mb: settings.max_resume_size_mb.toString(),
    supported_resume_formats: settings.supported_resume_formats,
  }
}

function ResumePolicyCard({ settings }: ResumePolicyCardProps) {
  const updateRecruitmentSettings = useUpdateRecruitmentSettings()

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<RecruitmentPolicyFormValues>({
    resolver: zodResolver(recruitmentPolicyFormSchema),
    defaultValues: settingsToFormValues(settings),
  })

  React.useEffect(() => {
    reset(settingsToFormValues(settings))
  }, [settings, reset])

  async function onSubmit(values: RecruitmentPolicyFormValues) {
    try {
      await updateRecruitmentSettings.mutateAsync({
        default_resume_score_threshold: Number(values.default_resume_score_threshold),
        enable_explainable_ai: values.enable_explainable_ai,
        max_resume_upload_count: Number(values.max_resume_upload_count),
        max_resume_size_mb: Number(values.max_resume_size_mb),
        supported_resume_formats: values.supported_resume_formats,
      })
      toast.success("Resume & ranking policy saved")
    } catch (error) {
      const message = error instanceof Error ? error.message : "Something went wrong"
      toast.error(message)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Resume & Ranking Policy</CardTitle>
        <CardDescription>Controls resume intake limits and AI ranking transparency.</CardDescription>
      </CardHeader>
      <CardContent>
        <form noValidate onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="resume-score-threshold">Default Resume Score Threshold</Label>
              <Input
                id="resume-score-threshold"
                type="number"
                min={0}
                max={100}
                aria-invalid={!!errors.default_resume_score_threshold}
                {...register("default_resume_score_threshold")}
              />
              {errors.default_resume_score_threshold && (
                <p className="text-xs text-destructive">
                  {errors.default_resume_score_threshold.message}
                </p>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="max-resume-upload-count">Max Resume Upload Count</Label>
              <Input
                id="max-resume-upload-count"
                type="number"
                min={1}
                aria-invalid={!!errors.max_resume_upload_count}
                {...register("max_resume_upload_count")}
              />
              {errors.max_resume_upload_count && (
                <p className="text-xs text-destructive">{errors.max_resume_upload_count.message}</p>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="max-resume-size-mb">Max Resume Size (MB)</Label>
              <Input
                id="max-resume-size-mb"
                type="number"
                min={1}
                aria-invalid={!!errors.max_resume_size_mb}
                {...register("max_resume_size_mb")}
              />
              {errors.max_resume_size_mb && (
                <p className="text-xs text-destructive">{errors.max_resume_size_mb.message}</p>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="enable-explainable-ai">Explainable AI</Label>
              <Controller
                control={control}
                name="enable_explainable_ai"
                render={({ field }) => (
                  <div className="flex h-8 items-center gap-2">
                    <Switch
                      id="enable-explainable-ai"
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                    <span className="text-sm text-muted-foreground">
                      Show recruiters why each candidate was ranked
                    </span>
                  </div>
                )}
              />
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>Supported Resume Formats</Label>
            <Controller
              control={control}
              name="supported_resume_formats"
              render={({ field }) => (
                <div className="flex flex-wrap gap-4">
                  {RESUME_FORMAT_OPTIONS.map((option) => {
                    const checked = field.value.includes(option.value)
                    return (
                      <label
                        key={option.value}
                        className="flex items-center gap-2 text-sm font-normal"
                      >
                        <Checkbox
                          checked={checked}
                          onCheckedChange={(next) => {
                            if (next) {
                              field.onChange([...field.value, option.value])
                            } else {
                              field.onChange(field.value.filter((value) => value !== option.value))
                            }
                          }}
                        />
                        {option.label}
                      </label>
                    )
                  })}
                </div>
              )}
            />
            {errors.supported_resume_formats && (
              <p className="text-xs text-destructive">{errors.supported_resume_formats.message}</p>
            )}
          </div>

          <div>
            <Button type="submit" isLoading={isSubmitting}>
              Save Resume Policy
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

export { ResumePolicyCard }
