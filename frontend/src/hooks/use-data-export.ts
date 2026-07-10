import { useMutation } from "@tanstack/react-query"

import { dataExportService } from "@/services/settings.service"
import type { ApiError } from "@/types"

export function useExportCandidates() {
  return useMutation<void, ApiError, void>({ mutationFn: () => dataExportService.exportCandidates() })
}

export function useExportAssessments() {
  return useMutation<void, ApiError, void>({ mutationFn: () => dataExportService.exportAssessments() })
}

export function useExportAuditLog() {
  return useMutation<void, ApiError, void>({ mutationFn: () => dataExportService.exportAuditLog() })
}
