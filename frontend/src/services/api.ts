import axios, { type AxiosRequestConfig } from "axios"

import { apiClient } from "@/services/axios"
import type { ApiError } from "@/types"

export function toApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as
      | { detail?: unknown; message?: string }
      | undefined
    const detailMessage = typeof data?.detail === "string" ? data.detail : undefined

    return {
      status: error.response?.status ?? 0,
      message: detailMessage ?? data?.message ?? error.message ?? "An unexpected error occurred.",
      detail: data?.detail,
    }
  }

  return {
    status: 0,
    message: error instanceof Error ? error.message : "An unexpected error occurred.",
  }
}

/** Thin, typed wrapper around the axios client — every service builds on this. */
export const api = {
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    try {
      const { data } = await apiClient.get<T>(url, config)
      return data
    } catch (error) {
      throw toApiError(error)
    }
  },

  async post<T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig): Promise<T> {
    try {
      const { data } = await apiClient.post<T>(url, body, config)
      return data
    } catch (error) {
      throw toApiError(error)
    }
  },

  async put<T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig): Promise<T> {
    try {
      const { data } = await apiClient.put<T>(url, body, config)
      return data
    } catch (error) {
      throw toApiError(error)
    }
  },

  async patch<T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig): Promise<T> {
    try {
      const { data } = await apiClient.patch<T>(url, body, config)
      return data
    } catch (error) {
      throw toApiError(error)
    }
  },

  async delete<T = void>(url: string, config?: AxiosRequestConfig): Promise<T> {
    try {
      const { data } = await apiClient.delete<T>(url, config)
      return data
    } catch (error) {
      throw toApiError(error)
    }
  },
}
