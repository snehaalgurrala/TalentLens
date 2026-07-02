"use client"

import * as React from "react"
import { usePathname } from "next/navigation"

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"

function segmentToLabel(segment: string): string {
  return segment
    .replace(/-/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

/** Derives a breadcrumb trail from the current pathname — override with explicit `items` when needed. */
function BreadcrumbArea({
  items,
}: {
  items?: { label: string; href?: string }[]
}) {
  const pathname = usePathname()

  const trail =
    items ??
    pathname
      .split("/")
      .filter(Boolean)
      .map((segment, index, segments) => ({
        label: segmentToLabel(segment),
        href: `/${segments.slice(0, index + 1).join("/")}`,
      }))

  if (trail.length === 0) return null

  return (
    <Breadcrumb>
      <BreadcrumbList>
        {trail.map((item, index) => {
          const isLast = index === trail.length - 1
          return (
            <React.Fragment key={item.href ?? item.label}>
              <BreadcrumbItem>
                {isLast || !item.href ? (
                  <BreadcrumbPage>{item.label}</BreadcrumbPage>
                ) : (
                  <BreadcrumbLink href={item.href}>{item.label}</BreadcrumbLink>
                )}
              </BreadcrumbItem>
              {!isLast && <BreadcrumbSeparator />}
            </React.Fragment>
          )
        })}
      </BreadcrumbList>
    </Breadcrumb>
  )
}

export { BreadcrumbArea }
