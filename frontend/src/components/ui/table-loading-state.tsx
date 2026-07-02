import * as React from "react"

import { Skeleton } from "@/components/ui/skeleton"
import { TableCell, TableRow } from "@/components/ui/table"

export interface TableLoadingStateProps {
  rows?: number
  columns: number
}

function TableLoadingState({ rows = 5, columns }: TableLoadingStateProps) {
  return (
    <>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <TableRow key={rowIndex} className="hover:bg-transparent">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <TableCell key={colIndex}>
              <Skeleton className="h-4 w-full max-w-40" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  )
}

export { TableLoadingState }
