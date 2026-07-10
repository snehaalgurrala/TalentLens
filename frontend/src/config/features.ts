/** Frontend feature flags for capabilities the backend doesn't support yet. */
export const FEATURES = {
  /** No `/auth/forgot-password` or `/auth/reset-password` endpoint exists yet. */
  forgotPasswordEnabled: false,
  /** No avatar/profile-photo upload endpoint exists yet (org logo upload does). */
  avatarUploadEnabled: false,
  /** No MFA enrollment/verification endpoint exists yet — spec calls this out as a future item explicitly. */
  mfaEnabled: false,
  /** No payment/plan-management backend exists — Billing ships as a usage-only placeholder ("Phase 7"). */
  billingPaymentsEnabled: false,
} as const
