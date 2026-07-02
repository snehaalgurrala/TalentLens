"use client"

import * as React from "react"
import { Search, X } from "lucide-react"

import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"

export interface SearchInputProps
  extends Omit<React.ComponentProps<typeof Input>, "type"> {
  onClear?: () => void
}

function SearchInput({ className, onClear, value, ...props }: SearchInputProps) {
  const hasValue = value !== undefined && value !== ""

  return (
    <div className="relative">
      <Search
        className="pointer-events-none absolute inset-y-0 left-2.5 my-auto size-4 text-muted-foreground"
        aria-hidden="true"
      />
      <Input
        type="search"
        value={value}
        className={cn(
          "pl-8 [&::-webkit-search-cancel-button]:appearance-none",
          onClear && "pr-9",
          className
        )}
        {...props}
      />
      {onClear && hasValue && (
        <button
          type="button"
          onClick={onClear}
          className="absolute inset-y-0 right-0 flex w-9 items-center justify-center text-muted-foreground transition-colors hover:text-foreground focus-visible:text-foreground focus-visible:outline-none"
          aria-label="Clear search"
        >
          <X className="size-4" aria-hidden="true" />
        </button>
      )}
    </div>
  )
}

export { SearchInput }
