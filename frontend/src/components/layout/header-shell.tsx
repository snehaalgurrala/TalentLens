import * as React from "react"

import { cn } from "@/lib/utils"

export interface HeaderShellProps extends React.ComponentProps<"header"> {
  left?: React.ReactNode
  right?: React.ReactNode
  sticky?: boolean
}

function HeaderShell({
  left,
  right,
  sticky = false,
  className,
  ...props
}: HeaderShellProps) {
  return (
    <header
      data-slot="header-shell"
      className={cn(
        "flex h-14 items-center justify-between gap-4 border-b border-border px-4 sm:px-6",
        sticky
          ? "sticky top-0 z-(--z-sticky) bg-surface/80 backdrop-blur-sm"
          : "bg-surface",
        className
      )}
      {...props}
    >
      <div className="flex min-w-0 items-center gap-3">{left}</div>
      <div className="flex shrink-0 items-center gap-3">{right}</div>
    </header>
  )
}

export { HeaderShell }
