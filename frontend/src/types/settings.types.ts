// ── Recruitment Settings (Settings > Recruitment) ──────────────────────────

export interface RecruitmentSettings {
  id: string
  org_id: string
  default_resume_score_threshold: number
  enable_explainable_ai: boolean
  max_resume_upload_count: number
  max_resume_size_mb: number
  supported_resume_formats: string[]
  created_at: string
  updated_at: string
}

export interface RecruitmentSettingsUpdate {
  default_resume_score_threshold?: number
  enable_explainable_ai?: boolean
  max_resume_upload_count?: number
  max_resume_size_mb?: number
  supported_resume_formats?: string[]
}

// ── Assessment Configuration (Settings > Assessment) ────────────────────────

export interface AssessmentConfig {
  id: string
  org_id: string
  read_aloud_reference_sentence: string
  listen_repeat_reference_sentence: string
  created_at: string
  updated_at: string
}

export interface AssessmentConfigUpdate {
  read_aloud_reference_sentence?: string
  listen_repeat_reference_sentence?: string
}

// ── Platform AI Configuration (Settings > AI, SUPER_ADMIN only) ─────────────

export interface PlatformAIConfig {
  id: string
  llm_provider: string
  llm_model: string
  temperature: number
  max_tokens: number
  prompt_logging_enabled: boolean
  embedding_model: string
  similarity_threshold: number
  reranking_enabled: boolean
  explainable_ai_enabled: boolean
  retention_policy_days: number
  retention_policy_notes: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
  /** True when this update changed embedding_model — the change needs an
   * app restart to take effect (the embedding model loads once at startup). */
  restart_required: boolean
}

export interface PlatformAIConfigUpdate {
  llm_provider?: string
  llm_model?: string
  temperature?: number
  max_tokens?: number
  prompt_logging_enabled?: boolean
  embedding_model?: string
  similarity_threshold?: number
  reranking_enabled?: boolean
  explainable_ai_enabled?: boolean
  retention_policy_days?: number
  retention_policy_notes?: string
}

// ── Platform Email Configuration (Settings > Email, SUPER_ADMIN only) ───────

export type EmailTestResult = "success" | "failure"

export interface PlatformEmailConfig {
  id: string
  smtp_host: string
  smtp_port: number
  smtp_username: string
  smtp_from_email: string
  smtp_from_name: string
  smtp_tls: boolean
  smtp_ssl: boolean
  is_configured: boolean
  has_password: boolean
  last_test_at: string | null
  last_test_status: EmailTestResult | null
  last_test_error: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface PlatformEmailConfigUpdate {
  smtp_host?: string
  smtp_port?: number
  smtp_username?: string
  smtp_password?: string
  smtp_from_email?: string
  smtp_from_name?: string
  smtp_tls?: boolean
  smtp_ssl?: boolean
}

export interface SendTestEmailRequest {
  to_email: string
}

export interface SendTestEmailResponse {
  success: boolean
  error: string | null
}

// ── Notification Preferences (Settings > Notifications) ─────────────────────

export interface NotificationPreference {
  id: string
  user_id: string
  assessment_completed: boolean
  assessment_started: boolean
  invitation_sent: boolean
  invitation_opened: boolean
  candidate_shortlisted: boolean
  ai_ranking_completed: boolean
  daily_summary: boolean
  weekly_summary: boolean
  email_enabled: boolean
  in_app_enabled: boolean
  created_at: string
  updated_at: string
}

export type NotificationPreferenceUpdate = Partial<
  Omit<NotificationPreference, "id" | "user_id" | "created_at" | "updated_at">
>

// ── Sessions (Settings > Security) ───────────────────────────────────────────

export interface UserSession {
  id: string
  device_label: string | null
  user_agent: string | null
  ip_address: string | null
  created_at: string
  last_seen_at: string
  is_current: boolean
}

// ── System Health (Settings > System Health, SUPER_ADMIN only) ──────────────

export interface CeleryHealth {
  status: "ok" | "down"
  worker_count: number
}

export interface DiskHealth {
  used_gb: number
  total_gb: number
  percent_used: number
}

export interface SystemHealthChecks {
  database: "ok" | "error"
  redis: "ok" | "error" | "not_initialized"
  celery_workers: CeleryHealth
  whisper_model: "loaded" | "not_loaded"
  storage: "ok" | "error"
  disk: DiskHealth
  queue_length: number
}

export interface SystemHealthResponse {
  status: "ok" | "degraded"
  environment: string
  version: string
  build: string
  timestamp: string
  checks: SystemHealthChecks
}

// ── Billing (Settings > Billing) ─────────────────────────────────────────────

export interface BillingUsage {
  users_count: number
  storage_used_mb: number
  assessments_used: number
  embedding_operations_count: number
  plan_name: "Coming Soon"
  period_start: string
  period_end: string
}

// ── Audit Log (Settings > Audit Log) ─────────────────────────────────────────

export interface AuditLogEntry {
  id: string
  org_id: string | null
  actor_id: string | null
  actor_name: string | null
  action: string
  entity_type: string
  entity_id: string | null
  event_metadata: Record<string, unknown> | null
  ip_address: string | null
  result: string
  created_at: string
}

export interface AuditLogListResponse {
  items: AuditLogEntry[]
  total: number
  limit: number
  offset: number
}

export interface AuditLogFilters {
  org_id?: string
  actor_id?: string
  action?: string
  entity_type?: string
  date_from?: string
  date_to?: string
  limit?: number
  offset?: number
}
