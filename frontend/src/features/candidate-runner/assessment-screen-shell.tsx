import * as React from "react"

import { siteConfig } from "@/config/site"
import { cn } from "@/lib/utils"

interface AssessmentScreenShellProps {
  children: React.ReactNode
  maxWidthClassName?: string
}

/** Centered, unauthenticated shell for candidate-facing screens with no section progress header. */
function AssessmentScreenShell({ children, maxWidthClassName }: AssessmentScreenShellProps) {
  return (
    <div className="flex min-h-dvh w-full items-center justify-center bg-background px-4 py-12">
      <div className={cn("flex w-full max-w-lg flex-col gap-6", maxWidthClassName)}>
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

export { AssessmentScreenShell }
