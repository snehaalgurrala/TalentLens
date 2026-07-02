import * as React from "react"

import { cn } from "@/lib/utils"

/** Scrollable region to the right of the sidebar, below the header. */
function ContentArea({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="content-area"
      className={cn("flex-1 overflow-y-auto", className)}
      {...props}
    />
  )
}

export { ContentArea }
