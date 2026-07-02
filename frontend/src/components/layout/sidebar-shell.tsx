"use client"

import * as React from "react"
import { motion } from "framer-motion"
import { ChevronLeft, ChevronRight } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  sidebarWidthVariants,
  SIDEBAR_COLLAPSED_WIDTH,
  SIDEBAR_EXPANDED_WIDTH,
} from "@/design-system/motion/sidebar-variants"

export interface SidebarShellProps {
  children: React.ReactNode
  collapsed?: boolean
  onCollapsedChange?: (collapsed: boolean) => void
  header?: React.ReactNode
  footer?: React.ReactNode
  className?: string
}

function SidebarShell({
  children,
  collapsed: collapsedProp,
  onCollapsedChange,
  header,
  footer,
  className,
}: SidebarShellProps) {
  const [collapsedState, setCollapsedState] = React.useState(false)
  const collapsed = collapsedProp ?? collapsedState

  function toggle() {
    const next = !collapsed
    setCollapsedState(next)
    onCollapsedChange?.(next)
  }

  return (
    <motion.aside
      data-slot="sidebar-shell"
      data-collapsed={collapsed}
      initial={false}
      animate={collapsed ? "collapsed" : "expanded"}
      variants={sidebarWidthVariants}
      style={{
        width: collapsed ? SIDEBAR_COLLAPSED_WIDTH : SIDEBAR_EXPANDED_WIDTH,
      }}
      className={cn(
        "flex h-full shrink-0 flex-col overflow-hidden border-r border-border bg-surface",
        className
      )}
    >
      {header && (
        <div className="flex h-14 shrink-0 items-center border-b border-border px-3">
          {header}
        </div>
      )}

      <nav className="flex-1 overflow-y-auto p-2">{children}</nav>

      {footer && (
        <div className="shrink-0 border-t border-border p-2">{footer}</div>
      )}

      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        onClick={toggle}
        className="m-2 self-end"
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        aria-expanded={!collapsed}
      >
        {collapsed ? (
          <ChevronRight className="size-4" aria-hidden="true" />
        ) : (
          <ChevronLeft className="size-4" aria-hidden="true" />
        )}
      </Button>
    </motion.aside>
  )
}

export { SidebarShell }
