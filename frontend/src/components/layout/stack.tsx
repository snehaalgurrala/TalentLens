import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const stackVariants = cva("flex", {
  variants: {
    direction: {
      row: "flex-row",
      column: "flex-col",
    },
    gap: {
      none: "gap-0",
      xs: "gap-1",
      sm: "gap-2",
      md: "gap-4",
      lg: "gap-6",
      xl: "gap-8",
    },
    align: {
      start: "items-start",
      center: "items-center",
      end: "items-end",
      stretch: "items-stretch",
    },
    justify: {
      start: "justify-start",
      center: "justify-center",
      end: "justify-end",
      between: "justify-between",
      around: "justify-around",
    },
    wrap: {
      true: "flex-wrap",
      false: "flex-nowrap",
    },
  },
  defaultVariants: {
    direction: "column",
    gap: "md",
    align: "stretch",
    justify: "start",
    wrap: false,
  },
})

export interface StackProps
  extends React.ComponentProps<"div">,
    VariantProps<typeof stackVariants> {}

function Stack({
  className,
  direction,
  gap,
  align,
  justify,
  wrap,
  ...props
}: StackProps) {
  return (
    <div
      data-slot="stack"
      className={cn(
        stackVariants({ direction, gap, align, justify, wrap }),
        className
      )}
      {...props}
    />
  )
}

export { Stack, stackVariants }
