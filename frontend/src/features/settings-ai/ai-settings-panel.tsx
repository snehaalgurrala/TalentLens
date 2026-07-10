"use client"

import * as React from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { Controller, useForm } from "react-hook-form"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { DashboardErrorState } from "@/features/dashboard"
import { usePlatformAIConfig, useUpdatePlatformAIConfig } from "@/hooks"
import type { PlatformAIConfig, PlatformAIConfigUpdate } from "@/types"

import { aiSettingsFormSchema, type AISettingsFormValues } from "./schemas"

const LLM_PROVIDER_OPTIONS = [
  { value: "none", label: "None" },
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
]

const EMBEDDING_MODEL_OPTIONS = [
  "text-embedding-3-small",
  "text-embedding-3-large",
  "all-MiniLM-L6-v2",
]

function configToFormValues(config: PlatformAIConfig): AISettingsFormValues {
  return {
    llm_provider: config.llm_provider,
    llm_model: config.llm_model,
    temperature: config.temperature.toString(),
    max_tokens: config.max_tokens.toString(),
    prompt_logging_enabled: config.prompt_logging_enabled,
    embedding_model: config.embedding_model,
    similarity_threshold: config.similarity_threshold.toString(),
    reranking_enabled: config.reranking_enabled,
    explainable_ai_enabled: config.explainable_ai_enabled,
  }
}

function toPayload(values: AISettingsFormValues): PlatformAIConfigUpdate {
  return {
    llm_provider: values.llm_provider,
    llm_model: values.llm_model.trim(),
    temperature: Number(values.temperature),
    max_tokens: Number(values.max_tokens),
    prompt_logging_enabled: values.prompt_logging_enabled,
    embedding_model: values.embedding_model.trim(),
    similarity_threshold: Number(values.similarity_threshold),
    reranking_enabled: values.reranking_enabled,
    explainable_ai_enabled: values.explainable_ai_enabled,
  }
}

function AISettingsPanelSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-4 w-72" />
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-8 w-full" />
        ))}
      </CardContent>
    </Card>
  )
}

function AISettingsPanel() {
  const { data, isLoading, isError, error, refetch } = usePlatformAIConfig()
  const updateConfig = useUpdatePlatformAIConfig()

  const {
    register,
    handleSubmit,
    control,
    reset,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<AISettingsFormValues>({
    resolver: zodResolver(aiSettingsFormSchema),
    defaultValues: {
      llm_provider: "none",
      llm_model: "",
      temperature: "0",
      max_tokens: "0",
      prompt_logging_enabled: false,
      embedding_model: "",
      similarity_threshold: "0",
      reranking_enabled: false,
      explainable_ai_enabled: false,
    },
  })

  React.useEffect(() => {
    if (data) reset(configToFormValues(data))
  }, [data, reset])

  async function onSubmit(values: AISettingsFormValues) {
    try {
      const result = await updateConfig.mutateAsync(toPayload(values))
      toast.success("AI configuration updated")
      if (result.restart_required) {
        toast.warning("This change requires an app restart to take effect.")
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Something went wrong"
      toast.error(message)
    }
  }

  if (isLoading) return <AISettingsPanelSkeleton />
  if (isError) return <DashboardErrorState error={error} onRetry={() => void refetch()} />

  return (
    <Card>
      <form onSubmit={handleSubmit(onSubmit)}>
        <CardHeader>
          <CardTitle>AI Configuration</CardTitle>
          <CardDescription>
            Controls the LLM and embedding pipeline used across the platform. Visible to Super Admins
            only.
          </CardDescription>
        </CardHeader>

        <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ai-llm-provider">LLM Provider</Label>
            <Controller
              control={control}
              name="llm_provider"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="ai-llm-provider" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {LLM_PROVIDER_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {errors.llm_provider && (
              <p className="text-xs text-destructive">{errors.llm_provider.message}</p>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ai-llm-model">LLM Model</Label>
            <Input id="ai-llm-model" aria-invalid={!!errors.llm_model} {...register("llm_model")} />
            {errors.llm_model && <p className="text-xs text-destructive">{errors.llm_model.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ai-temperature">Temperature</Label>
            <Input
              id="ai-temperature"
              type="number"
              min={0}
              max={2}
              step={0.1}
              aria-invalid={!!errors.temperature}
              {...register("temperature")}
            />
            {errors.temperature && (
              <p className="text-xs text-destructive">{errors.temperature.message}</p>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ai-max-tokens">Max Tokens</Label>
            <Input
              id="ai-max-tokens"
              type="number"
              min={1}
              step={1}
              aria-invalid={!!errors.max_tokens}
              {...register("max_tokens")}
            />
            {errors.max_tokens && (
              <p className="text-xs text-destructive">{errors.max_tokens.message}</p>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ai-embedding-model">Embedding Model</Label>
            <div className="flex gap-2">
              <Input
                id="ai-embedding-model"
                className="flex-1"
                aria-invalid={!!errors.embedding_model}
                {...register("embedding_model")}
              />
              <Select onValueChange={(value) => setValue("embedding_model", value, { shouldDirty: true })}>
                <SelectTrigger className="w-auto" aria-label="Common embedding models">
                  <SelectValue placeholder="Presets" />
                </SelectTrigger>
                <SelectContent>
                  {EMBEDDING_MODEL_OPTIONS.map((model) => (
                    <SelectItem key={model} value={model}>
                      {model}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <p className="text-xs text-muted-foreground">
              Changing this requires an app restart to take effect.
            </p>
            {errors.embedding_model && (
              <p className="text-xs text-destructive">{errors.embedding_model.message}</p>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ai-similarity-threshold">Similarity Threshold</Label>
            <Input
              id="ai-similarity-threshold"
              type="number"
              min={0}
              max={1}
              step={0.01}
              aria-invalid={!!errors.similarity_threshold}
              {...register("similarity_threshold")}
            />
            {errors.similarity_threshold && (
              <p className="text-xs text-destructive">{errors.similarity_threshold.message}</p>
            )}
          </div>

          <div className="flex items-center justify-between gap-4 rounded-lg border border-border p-3 sm:col-span-2">
            <div className="flex flex-col gap-0.5">
              <Label htmlFor="ai-prompt-logging">Prompt Logging</Label>
              <p className="text-xs text-muted-foreground">
                Store LLM prompts and responses for debugging and auditing.
              </p>
            </div>
            <Controller
              control={control}
              name="prompt_logging_enabled"
              render={({ field }) => (
                <Switch
                  id="ai-prompt-logging"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              )}
            />
          </div>

          <div className="flex items-center justify-between gap-4 rounded-lg border border-border p-3 sm:col-span-2">
            <div className="flex flex-col gap-0.5">
              <Label htmlFor="ai-reranking">Reranking</Label>
              <p className="text-xs text-muted-foreground">
                No active reranking pipeline yet — this only stores your preference.
              </p>
            </div>
            <Controller
              control={control}
              name="reranking_enabled"
              render={({ field }) => (
                <Switch id="ai-reranking" checked={field.value} onCheckedChange={field.onChange} />
              )}
            />
          </div>

          <div className="flex items-center justify-between gap-4 rounded-lg border border-border p-3 sm:col-span-2">
            <div className="flex flex-col gap-0.5">
              <Label htmlFor="ai-explainable">Explainable AI</Label>
              <p className="text-xs text-muted-foreground">
                Show candidate match-analysis explanations elsewhere in the app.
              </p>
            </div>
            <Controller
              control={control}
              name="explainable_ai_enabled"
              render={({ field }) => (
                <Switch
                  id="ai-explainable"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              )}
            />
          </div>
        </CardContent>

        <CardFooter>
          <Button type="submit" isLoading={isSubmitting}>
            Save Changes
          </Button>
        </CardFooter>
      </form>
    </Card>
  )
}

export { AISettingsPanel }
