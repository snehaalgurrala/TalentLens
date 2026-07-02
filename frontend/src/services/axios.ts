import axios from "axios"

import { env } from "@/config/env"

export const API_BASE_URL = `${env.apiUrl}/api/v1`

/** Main client — carries the request/response interceptors set up in `interceptors.ts`. */
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
})

/** Bare client used only for the token-refresh call, so it never recurses into the 401 handler. */
export const refreshClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
})
