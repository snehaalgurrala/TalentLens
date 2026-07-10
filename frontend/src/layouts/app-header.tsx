"use client"

import * as React from "react"
import { MenuIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { HeaderShell } from "@/components/layout/header-shell"
import { NotificationBell } from "@/features/notifications"
import { useSidebar } from "@/hooks/use-sidebar"
import { BreadcrumbArea } from "@/layouts/breadcrumb-area"
import { UserProfileDropdown } from "@/layouts/user-profile-dropdown"

function AppHeader() {
  const { setMobileOpen } = useSidebar()

  return (
    <HeaderShell
      sticky
      left={
        <>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            className="lg:hidden"
            aria-label="Open navigation"
            onClick={() => setMobileOpen(true)}
          >
            <MenuIcon aria-hidden="true" />
          </Button>
          <BreadcrumbArea />
        </>
      }
      right={
        <div className="flex items-center gap-1">
          <NotificationBell />
          <UserProfileDropdown />
        </div>
      }
    />
  )
}

export { AppHeader }
