import { api } from "@/services/api"
import { apiClient } from "@/services/axios"
import type {
  AssessmentConfig,
  AssessmentConfigUpdate,
  AuditLogFilters,
  AuditLogListResponse,
  BillingUsage,
  NotificationPreference,
  NotificationPreferenceUpdate,
  PlatformAIConfig,
  PlatformAIConfigUpdate,
  PlatformEmailConfig,
  PlatformEmailConfigUpdate,
  RecruitmentSettings,
  RecruitmentSettingsUpdate,
  SendTestEmailResponse,
  SystemHealthResponse,
  UserSession,
} from "@/types"

export const recruitmentSettingsService = {
  get: () => api.get<RecruitmentSettings>("/recruitment-settings"),
  update: (data: RecruitmentSettingsUpdate) =>
    api.patch<RecruitmentSettings>("/recruitment-settings", data),
}

export const assessmentConfigService = {
  get: () => api.get<AssessmentConfig>("/assessment-config"),
  update: (data: AssessmentConfigUpdate) => api.patch<AssessmentConfig>("/assessment-config", data),
}

export const platformAIConfigService = {
  get: () => api.get<PlatformAIConfig>("/platform/ai-config"),
  update: (data: PlatformAIConfigUpdate) => api.patch<PlatformAIConfig>("/platform/ai-config", data),
}

export const platformEmailConfigService = {
  get: () => api.get<PlatformEmailConfig>("/platform/email-config"),
  update: (data: PlatformEmailConfigUpdate) =>
    api.patch<PlatformEmailConfig>("/platform/email-config", data),
  sendTest: (toEmail: string) =>
    api.post<SendTestEmailResponse>("/platform/email-config/test", { to_email: toEmail }),
}

export const notificationPreferenceService = {
  get: () => api.get<NotificationPreference>("/notification-preferences/me"),
  update: (data: NotificationPreferenceUpdate) =>
    api.patch<NotificationPreference>("/notification-preferences/me", data),
}

export const sessionService = {
  listMine: () => api.get<UserSession[]>("/sessions/me"),
  revoke: (sessionId: string) => api.delete<void>(`/sessions/me/${sessionId}`),
  revokeOthers: () => api.post<void>("/sessions/me/revoke-others"),
}

export const systemHealthService = {
  get: () => api.get<SystemHealthResponse>("/system/health"),
}

export const billingService = {
  getUsage: () => api.get<BillingUsage>("/billing/usage"),
}

export const auditLogService = {
  list: (filters?: AuditLogFilters) => api.get<AuditLogListResponse>("/audit-log", { params: filters }),
}

async function downloadCsv(url: string, filename: string) {
  const { data } = await apiClient.get(url, { responseType: "blob" })
  const objectUrl = URL.createObjectURL(data as Blob)
  const link = document.createElement("a")
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(objectUrl)
}

export const dataExportService = {
  exportCandidates: () => downloadCsv("/exports/candidates.csv", "candidates.csv"),
  exportAssessments: () => downloadCsv("/exports/assessments.csv", "assessments.csv"),
  exportAuditLog: () => downloadCsv("/exports/audit-log.csv", "audit-log.csv"),
}
