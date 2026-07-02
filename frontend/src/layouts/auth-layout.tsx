import * as React from "react"

import { siteConfig } from "@/config/site"

/** Centered, unauthenticated shell for login/register/forgot-password/invite pages. */
function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh w-full items-center justify-center bg-background px-4 py-12">
      <div className="flex w-full max-w-sm flex-col gap-6">
        <div className="flex items-center justify-center gap-2 text-lg font-semibold text-foreground">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary text-sm text-primary-foreground">
            {siteConfig.name.charAt(0)}
          </span>
          {siteConfig.name}
        </div>
        {children}
      </div>
    </div>
  )
}

export { AuthLayout }
