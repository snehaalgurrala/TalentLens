"use client"

import * as React from "react"
import { Bell, Home, Search, Settings, Users } from "lucide-react"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { HeaderShell } from "@/components/layout/header-shell"
import { SidebarShell } from "@/components/layout/sidebar-shell"
import { Stack } from "@/components/layout/stack"
import { Row, Section } from "../_components/section"

const navItems = [
  { icon: Home, label: "Dashboard" },
  { icon: Users, label: "Candidates" },
  { icon: Search, label: "Campaigns" },
  { icon: Settings, label: "Settings" },
]

function LayoutSection() {
  const [collapsed, setCollapsed] = React.useState(false)

  return (
    <Section
      id="layout"
      title="Layout primitives"
      description="Container and PageWrapper are structural (this page is itself wrapped in a PageWrapper) — Stack, Sidebar shell, and Header shell are shown live below."
    >
      <Row label="Stack">
        <Stack direction="row" gap="sm">
          <div className="size-8 rounded-md bg-primary/20" />
          <div className="size-8 rounded-md bg-secondary/20" />
          <div className="size-8 rounded-md bg-success/20" />
        </Stack>
      </Row>

      <div className="overflow-hidden rounded-lg border border-border">
        <div className="flex h-80">
          <SidebarShell
            collapsed={collapsed}
            onCollapsedChange={setCollapsed}
            header={
              <span className="text-sm font-semibold text-foreground">
                {collapsed ? "TL" : "TalentLens"}
              </span>
            }
            footer={
              <div className="flex items-center gap-2 px-1">
                <Avatar size="sm">
                  <AvatarFallback>JD</AvatarFallback>
                </Avatar>
                {!collapsed && (
                  <span className="text-caption text-muted-foreground">
                    Jane Doe
                  </span>
                )}
              </div>
            }
          >
            <ul className="flex flex-col gap-1">
              {navItems.map(({ icon: Icon, label }) => (
                <li key={label}>
                  <Button
                    variant="ghost"
                    className="w-full justify-start gap-2"
                  >
                    <Icon className="size-4 shrink-0" aria-hidden="true" />
                    {!collapsed && label}
                  </Button>
                </li>
              ))}
            </ul>
          </SidebarShell>

          <div className="flex flex-1 flex-col">
            <HeaderShell
              left={
                <span className="text-sm font-medium text-foreground">
                  Candidates
                </span>
              }
              right={
                <Button variant="ghost" size="icon-sm" aria-label="Notifications">
                  <Bell className="size-4" aria-hidden="true" />
                </Button>
              }
            />
            <div className="flex flex-1 items-center justify-center text-caption text-muted-foreground">
              Page content area
            </div>
          </div>
        </div>
      </div>
    </Section>
  )
}

export { LayoutSection }
