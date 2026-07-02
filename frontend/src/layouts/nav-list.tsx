"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"

import { cn } from "@/lib/utils"
import { dashboardNavItems } from "@/layouts/nav-items"

function isActiveRoute(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`)
}

export interface NavListProps {
  collapsed?: boolean
  onNavigate?: () => void
}

function NavList({ collapsed = false, onNavigate }: NavListProps) {
  const pathname = usePathname()

  return (
    <ul className="flex flex-col gap-1">
      {dashboardNavItems.map((item) => {
        const active = isActiveRoute(pathname, item.href)
        const Icon = item.icon
        return (
          <li key={item.href}>
            <Link
              href={item.href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              title={collapsed ? item.title : undefined}
              className={cn(
                "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium text-muted-foreground transition-colors outline-none",
                "hover:bg-muted hover:text-foreground",
                "focus-visible:bg-muted focus-visible:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50",
                active && "bg-primary/10 text-primary hover:bg-primary/10 hover:text-primary"
              )}
            >
              <Icon className="size-4 shrink-0" aria-hidden="true" />
              {!collapsed && <span className="truncate">{item.title}</span>}
            </Link>
          </li>
        )
      })}
    </ul>
  )
}

export { NavList }
