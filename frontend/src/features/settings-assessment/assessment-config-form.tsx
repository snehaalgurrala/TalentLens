"use client"

import * as React from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useUpdateAssessmentConfig } from "@/hooks"
import type { AssessmentConfig } from "@/types"

import { assessmentConfigFormSchema, type AssessmentConfigFormValues } from "./schemas"

export interface AssessmentConfigFormProps {
  config: AssessmentConfig
}

function configToFormValues(config: AssessmentConfig): AssessmentConfigFormValues {
  return {
    read_aloud_reference_sentence: config.read_aloud_reference_sentence,
    listen_repeat_reference_sentence: config.listen_repeat_reference_sentence,
  }
}

function AssessmentConfigForm({ config }: AssessmentConfigFormProps) {
  const updateAssessmentConfig = useUpdateAssessmentConfig()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<AssessmentConfigFormValues>({
    resolver: zodResolver(assessmentConfigFormSchema),
    defaultValues: configToFormValues(config),
  })

  React.useEffect(() => {
    reset(configToFormValues(config))
  }, [config, reset])

  async function onSubmit(values: AssessmentConfigFormValues) {
    try {
      await updateAssessmentConfig.mutateAsync(values)
      toast.success("Assessment configuration saved")
    } catch (error) {
      const message = error instanceof Error ? error.message : "Something went wrong"
      toast.error(message)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Assessment Reference Sentences</CardTitle>
        <CardDescription>
          Candidates read or repeat these sentences during the communication assessment.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form noValidate onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="read-aloud-sentence">Read Aloud Reference Sentence</Label>
            <Textarea
              id="read-aloud-sentence"
              rows={3}
              aria-invalid={!!errors.read_aloud_reference_sentence}
              {...register("read_aloud_reference_sentence")}
            />
            {errors.read_aloud_reference_sentence && (
              <p className="text-xs text-destructive">
                {errors.read_aloud_reference_sentence.message}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="listen-repeat-sentence">Listen & Repeat Reference Sentence</Label>
            <Textarea
              id="listen-repeat-sentence"
              rows={3}
              aria-invalid={!!errors.listen_repeat_reference_sentence}
              {...register("listen_repeat_reference_sentence")}
            />
            {errors.listen_repeat_reference_sentence && (
              <p className="text-xs text-destructive">
                {errors.listen_repeat_reference_sentence.message}
              </p>
            )}
          </div>

          <div>
            <Button type="submit" isLoading={isSubmitting}>
              Save Changes
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

export { AssessmentConfigForm }
