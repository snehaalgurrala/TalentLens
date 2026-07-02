import type { AxiosError, InternalAxiosRequestConfig } from "axios"

import {
  clearSession,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
  setSessionCookie,
} from "@/lib/storage"
import { apiClient, refreshClient } from "@/services/axios"
import type { TokenResponse } from "@/types"

interface RetryableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

type AuthFailureHandler = () => void
let authFailureHandler: AuthFailureHandler | null = null

/** Called by AuthProvider so the interceptor can trigger logout + redirect without importing React. */
export function registerAuthFailureHandler(handler: AuthFailureHandler): void {
  authFailureHandler = handler
}

let isRefreshing = false
let pendingQueue: Array<{
  resolve: (token: string) => void
  reject: (error: unknown) => void
}> = []

function flushQueue(error: unknown, token: string | null) {
  pendingQueue.forEach(({ resolve, reject }) => {
    if (error || !token) reject(error)
    else resolve(token)
  })
  pendingQueue = []
}

const AUTH_ENDPOINTS = ["/auth/login", "/auth/register", "/auth/refresh"]

function isAuthEndpoint(url?: string): boolean {
  return Boolean(url && AUTH_ENDPOINTS.some((endpoint) => url.includes(endpoint)))
}

let interceptorsInstalled = false

/** Idempotent — safe to call from module scope or a provider's effect. */
export function setupInterceptors(): void {
  if (interceptorsInstalled) return
  interceptorsInstalled = true

  apiClient.interceptors.request.use((config) => {
    const token = getAccessToken()
    if (token) {
      config.headers.set("Authorization", `Bearer ${token}`)
    }
    return config
  })

  apiClient.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const originalRequest = error.config as RetryableConfig | undefined

      if (
        error.response?.status !== 401 ||
        !originalRequest ||
        originalRequest._retry ||
        isAuthEndpoint(originalRequest.url)
      ) {
        return Promise.reject(error)
      }

      const refreshToken = getRefreshToken()
      if (!refreshToken) {
        clearSession()
        authFailureHandler?.()
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          pendingQueue.push({
            resolve: (token) => {
              originalRequest._retry = true
              originalRequest.headers.set("Authorization", `Bearer ${token}`)
              resolve(apiClient(originalRequest))
            },
            reject,
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const { data } = await refreshClient.post<TokenResponse>("/auth/refresh", {
          refresh_token: refreshToken,
        })
        setAccessToken(data.access_token)
        setRefreshToken(data.refresh_token)
        setSessionCookie(true)
        flushQueue(null, data.access_token)

        originalRequest.headers.set("Authorization", `Bearer ${data.access_token}`)
        return apiClient(originalRequest)
      } catch (refreshError) {
        flushQueue(refreshError, null)
        clearSession()
        authFailureHandler?.()
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }
  )
}
