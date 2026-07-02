export type ParsingStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED"

export type EmbeddingStatus = "PENDING" | "GENERATING" | "READY" | "FAILED"

export interface JobDescription {
  id: string
  campaign_id: string
  created_by: string | null
  original_filename: string | null
  storage_path: string | null
  mime_type: string | null
  file_size: number | null
  raw_text: string
  structured_json: Record<string, unknown> | null
  parser_version: string | null
  parsed_at: string | null
  parsing_status: ParsingStatus
  parsing_error: string | null
  embedding_status: EmbeddingStatus
  embedding_model: string | null
  embedding_generated_at: string | null
  embedding_dimension: number | null
  is_deleted: boolean
  created_at: string
  updated_at: string
}

export interface JobDescriptionCreate {
  text: string
}
