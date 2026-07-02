import { api } from "@/services/api"
import type { Assessment, AssessmentCreate, AssessmentUpdate, PaginationParams } from "@/types"

export const assessmentService = {
  list: (params?: PaginationParams) => api.get<Assessment[]>("/assessments/", { params }),
  get: (assessmentId: string) => api.get<Assessment>(`/assessments/${assessmentId}`),
  create: (data: AssessmentCreate) => api.post<Assessment>("/assessments/", data),
  update: (assessmentId: string, data: AssessmentUpdate) =>
    api.patch<Assessment>(`/assessments/${assessmentId}`, data),
  remove: (assessmentId: string) => api.delete<void>(`/assessments/${assessmentId}`),
}
