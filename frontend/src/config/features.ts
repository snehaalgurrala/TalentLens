/** Frontend feature flags for capabilities the backend doesn't support yet. */
export const FEATURES = {
  /** No `/auth/forgot-password` or `/auth/reset-password` endpoint exists yet. */
  forgotPasswordEnabled: false,
} as const
