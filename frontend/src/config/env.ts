/**
 * Typed, validated access to environment variables.
 *
 * Only `NEXT_PUBLIC_*` variables are readable in the browser, so this module
 * only exposes those. Import `env` instead of touching `process.env` directly
 * elsewhere in the app.
 */

function requireEnv(name: string, value: string | undefined): string {
  if (!value || value.length === 0) {
    throw new Error(
      `Missing required environment variable: ${name}. Check your .env.local file.`
    )
  }
  return value
}

export const env = {
  apiUrl: requireEnv(
    "NEXT_PUBLIC_API_URL",
    process.env.NEXT_PUBLIC_API_URL
  ).replace(/\/+$/, ""),
  appName: process.env.NEXT_PUBLIC_APP_NAME ?? "TalentLens",
  appUrl: (process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000").replace(
    /\/+$/,
    ""
  ),
  isProduction: process.env.NODE_ENV === "production",
  isDevelopment: process.env.NODE_ENV === "development",
  isTest: process.env.NODE_ENV === "test",
} as const

export type Env = typeof env
