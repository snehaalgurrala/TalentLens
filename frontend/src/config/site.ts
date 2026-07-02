import { env } from "@/config/env"

export const siteConfig = {
  name: env.appName,
  titleTemplate: `%s | ${env.appName}`,
  description: "AI-powered recruitment intelligence platform.",
  url: env.appUrl,
} as const
