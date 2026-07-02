import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const gridVariants = cva("grid", {
  variants: {
    cols: {
      1: "grid-cols-1",
      2: "grid-cols-2",
      3: "grid-cols-3",
      4: "grid-cols-4",
      6: "grid-cols-6",
      12: "grid-cols-12",
    },
    colsSm: {
      1: "sm:grid-cols-1",
      2: "sm:grid-cols-2",
      3: "sm:grid-cols-3",
      4: "sm:grid-cols-4",
    },
    colsMd: {
      1: "md:grid-cols-1",
      2: "md:grid-cols-2",
      3: "md:grid-cols-3",
      4: "md:grid-cols-4",
      6: "md:grid-cols-6",
    },
    colsLg: {
      1: "lg:grid-cols-1",
      2: "lg:grid-cols-2",
      3: "lg:grid-cols-3",
      4: "lg:grid-cols-4",
      6: "lg:grid-cols-6",
      12: "lg:grid-cols-12",
    },
    gap: {
      none: "gap-0",
      sm: "gap-3",
      md: "gap-4",
      lg: "gap-6",
      xl: "gap-8",
    },
  },
  defaultVariants: {
    cols: 1,
    gap: "md",
  },
})

export interface GridProps
  extends React.ComponentProps<"div">,
    VariantProps<typeof gridVariants> {}

function Grid({
  className,
  cols,
  colsSm,
  colsMd,
  colsLg,
  gap,
  ...props
}: GridProps) {
  return (
    <div
      data-slot="grid"
      className={cn(
        gridVariants({ cols, colsSm, colsMd, colsLg, gap }),
        className
      )}
      {...props}
    />
  )
}

export { Grid, gridVariants }
