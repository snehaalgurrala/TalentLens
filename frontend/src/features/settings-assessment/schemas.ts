import { z } from "zod"

export const assessmentConfigFormSchema = z.object({
  read_aloud_reference_sentence: z.string().min(1, "Required").max(2000),
  listen_repeat_reference_sentence: z.string().min(1, "Required").max(2000),
})

export type AssessmentConfigFormValues = z.infer<typeof assessmentConfigFormSchema>
