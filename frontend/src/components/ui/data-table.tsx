"use client"

import * as React from "react"
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react"

import { cn } from "@/lib/utils"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { TableLoadingState } from "@/components/ui/table-loading-state"

export interface DataTableColumn<T> {
  key: string
  header: React.ReactNode
  sortable?: boolean
  align?: "left" | "right" | "center"
  className?: string
  render: (row: T) => React.ReactNode
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[]
  data: T[]
  getRowKey: (row: T) => string | number
  state?: "ready" | "loading" | "empty"
  loadingRows?: number
  emptyTitle?: string
  emptyDescription?: string
  emptyAction?: React.ReactNode
  sortKey?: string
  sortDirection?: "asc" | "desc"
  onSortChange?: (key: string) => void
  onRowClick?: (row: T) => void
  className?: string
}

const alignClass = {
  left: "text-left",
  center: "text-center",
  right: "text-right",
} as const

function DataTable<T>({
  columns,
  data,
  getRowKey,
  state = "ready",
  loadingRows = 5,
  emptyTitle = "No results",
  emptyDescription,
  emptyAction,
  sortKey,
  sortDirection,
  onSortChange,
  onRowClick,
  className,
}: DataTableProps<T>) {
  const isEmpty = state === "empty" || (state === "ready" && data.length === 0)

  return (
    <div data-slot="data-table" className={cn(className)}>
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((column) => (
              <TableHead
                key={column.key}
                className={cn(
                  column.align && alignClass[column.align],
                  column.className
                )}
              >
                {column.sortable ? (
                  <button
                    type="button"
                    onClick={() => onSortChange?.(column.key)}
                    className="inline-flex items-center gap-1 hover:text-foreground"
                  >
                    {column.header}
                    {sortKey === column.key ? (
                      sortDirection === "desc" ? (
                        <ArrowDown className="size-3.5" aria-hidden="true" />
                      ) : (
                        <ArrowUp className="size-3.5" aria-hidden="true" />
                      )
                    ) : (
                      <ArrowUpDown
                        className="size-3.5 text-muted-foreground/50"
                        aria-hidden="true"
                      />
                    )}
                  </button>
                ) : (
                  column.header
                )}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {state === "loading" && (
            <TableLoadingState rows={loadingRows} columns={columns.length} />
          )}
          {isEmpty && (
            <TableRow className="hover:bg-transparent">
              <TableCell colSpan={columns.length}>
                <TableEmptyState
                  title={emptyTitle}
                  description={emptyDescription}
                  action={emptyAction}
                />
              </TableCell>
            </TableRow>
          )}
          {state !== "loading" &&
            !isEmpty &&
            data.map((row) => (
              <TableRow
                key={getRowKey(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={cn(onRowClick && "cursor-pointer")}
              >
                {columns.map((column) => (
                  <TableCell
                    key={column.key}
                    className={cn(column.align && alignClass[column.align])}
                  >
                    {column.render(row)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
        </TableBody>
      </Table>
    </div>
  )
}

export { DataTable }
