import { z } from "zod"

// Numeric fields stay as raw strings here (HTML number inputs) — converted
// to numbers in ai-settings-panel.tsx::toPayload.
export const aiSettingsFormSchema = z.object({
  llm_provider: z.string().min(1, "Required"),
  llm_model: z.string().min(1, "Model is required").max(255),
  temperature: z
    .string()
    .min(1, "Required")
    .refine((v) => !Number.isNaN(Number(v)) && Number(v) >= 0 && Number(v) <= 2, {
      message: "Temperature must be between 0 and 2",
    }),
  max_tokens: z
    .string()
    .min(1, "Required")
    .refine((v) => !Number.isNaN(Number(v)) && Number(v) > 0 && Number.isInteger(Number(v)), {
      message: "Max tokens must be a positive whole number",
    }),
  prompt_logging_enabled: z.boolean(),
  embedding_model: z.string().min(1, "Embedding model is required").max(255),
  similarity_threshold: z
    .string()
    .min(1, "Required")
    .refine((v) => !Number.isNaN(Number(v)) && Number(v) >= 0 && Number(v) <= 1, {
      message: "Similarity threshold must be between 0 and 1",
    }),
  reranking_enabled: z.boolean(),
  explainable_ai_enabled: z.boolean(),
})

export type AISettingsFormValues = z.infer<typeof aiSettingsFormSchema>
