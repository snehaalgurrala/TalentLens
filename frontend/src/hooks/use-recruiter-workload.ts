import { useQuery } from "@tanstack/react-query"

import { recruiterWorkloadService } from "@/services/recruiter-workload.service"
import type { ApiError, RecruiterWorkloadResponse } from "@/types"

export const recruiterWorkloadKeys = {
  all: ["recruiter-workload"] as const,
}

export function useRecruiterWorkload() {
  return useQuery<RecruiterWorkloadResponse, ApiError>({
    queryKey: recruiterWorkloadKeys.all,
    queryFn: recruiterWorkloadService.get,
  })
}
