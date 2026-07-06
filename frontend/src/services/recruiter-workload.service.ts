import { api } from "@/services/api"
import type { RecruiterWorkloadResponse } from "@/types"

export const recruiterWorkloadService = {
  get: () => api.get<RecruiterWorkloadResponse>("/users/recruiter-workload"),
}
