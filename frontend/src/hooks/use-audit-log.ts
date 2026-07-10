import { useQuery } from "@tanstack/react-query"

import { auditLogService } from "@/services/settings.service"
import type { ApiError, AuditLogFilters, AuditLogListResponse } from "@/types"

export const auditLogKeys = {
  all: ["audit-log"] as const,
  list: (filters?: AuditLogFilters) => [...auditLogKeys.all, "list", filters ?? {}] as const,
}

export function useAuditLog(filters?: AuditLogFilters) {
  return useQuery<AuditLogListResponse, ApiError>({
    queryKey: auditLogKeys.list(filters),
    queryFn: () => auditLogService.list(filters),
  })
}
