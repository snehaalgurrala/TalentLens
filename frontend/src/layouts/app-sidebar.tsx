"use client"

import * as React from "react"
import Link from "next/link"

import { SidebarShell } from "@/components/layout/sidebar-shell"
import { siteConfig } from "@/config/site"
import { useSidebar } from "@/hooks/use-sidebar"
import { NavList } from "@/layouts/nav-list"

function AppSidebar() {
  const { collapsed, setCollapsed } = useSidebar()

  return (
    <SidebarShell
      collapsed={collapsed}
      onCollapsedChange={setCollapsed}
      className="hidden lg:flex"
      header={
        <Link
          href="/dashboard"
          className="flex items-center gap-2 overflow-hidden rounded-md px-1 text-sm font-semibold text-foreground focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary text-xs text-primary-foreground">
            {siteConfig.name.charAt(0)}
          </span>
          {!collapsed && <span className="truncate">{siteConfig.name}</span>}
        </Link>
      }
    >
      <NavList collapsed={collapsed} />
    </SidebarShell>
  )
}

export { AppSidebar }
