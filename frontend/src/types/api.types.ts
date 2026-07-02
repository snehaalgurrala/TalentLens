/** Shape of a normalized API error, regardless of the underlying transport error. */
export interface ApiError {
  status: number
  message: string
  detail?: unknown
}

/** Common pagination query params used by list endpoints (`skip`/`limit`). */
export interface PaginationParams {
  skip?: number
  limit?: number
}
