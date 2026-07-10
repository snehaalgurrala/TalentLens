"use client"

import * as React from "react"
import { useRouter, useSearchParams } from "next/navigation"

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { usePermissions } from "@/hooks"
import { AISettingsPanel } from "@/features/settings-ai"
import { AssessmentSettingsPanel } from "@/features/settings-assessment"
import { AuditLogPanel } from "@/features/settings-audit-log"
import { BillingPanel } from "@/features/settings-billing"
import { DataManagementPanel } from "@/features/settings-data-management"
import { EmailSettingsPanel } from "@/features/settings-email"
import { NotificationSettingsPanel } from "@/features/settings-notifications"
import { OrganizationSettingsPanel } from "@/features/settings-organization"
import { RecruitmentSettingsPanel } from "@/features/settings-recruitment"
import { SecuritySettingsPanel } from "@/features/settings-security"
import { SystemHealthPanel } from "@/features/settings-system-health"
import { UserManagementPanel } from "@/features/settings-users"
import type { UserRole } from "@/types"

interface SettingsTabDef {
  value: string
  label: string
  roles: UserRole[]
  Component: React.ComponentType
}

const ALL_ROLES: UserRole[] = ["CANDIDATE", "RECRUITER", "ORG_ADMIN", "SUPER_ADMIN"]

const SETTINGS_TABS: SettingsTabDef[] = [
  { value: "organization", label: "Organization", roles: ["ORG_ADMIN", "SUPER_ADMIN"], Component: OrganizationSettingsPanel },
  { value: "recruitment", label: "Recruitment", roles: ["ORG_ADMIN", "SUPER_ADMIN"], Component: RecruitmentSettingsPanel },
  { value: "assessment", label: "Assessment", roles: ["ORG_ADMIN", "SUPER_ADMIN"], Component: AssessmentSettingsPanel },
  { value: "ai", label: "AI Configuration", roles: ["SUPER_ADMIN"], Component: AISettingsPanel },
  { value: "email", label: "Email", roles: ["SUPER_ADMIN"], Component: EmailSettingsPanel },
  { value: "notifications", label: "Notifications", roles: ["RECRUITER", "ORG_ADMIN", "SUPER_ADMIN"], Component: NotificationSettingsPanel },
  { value: "security", label: "Security", roles: ALL_ROLES, Component: SecuritySettingsPanel },
  { value: "users", label: "Users", roles: ["ORG_ADMIN", "SUPER_ADMIN"], Component: UserManagementPanel },
  { value: "system-health", label: "System Health", roles: ["SUPER_ADMIN"], Component: SystemHealthPanel },
  { value: "billing", label: "Billing", roles: ["ORG_ADMIN", "SUPER_ADMIN"], Component: BillingPanel },
  { value: "audit-log", label: "Audit Log", roles: ["ORG_ADMIN", "SUPER_ADMIN"], Component: AuditLogPanel },
  { value: "data-management", label: "Data Management", roles: ["ORG_ADMIN", "SUPER_ADMIN"], Component: DataManagementPanel },
]

function SettingsView() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { hasAnyRole } = usePermissions()

  const visibleTabs = React.useMemo(
    () => SETTINGS_TABS.filter((tab) => hasAnyRole(...tab.roles)),
    [hasAnyRole]
  )

  const requestedTab = searchParams.get("tab")
  const activeTab =
    requestedTab && visibleTabs.some((t) => t.value === requestedTab)
      ? requestedTab
      : (visibleTabs[0]?.value ?? "security")

  function handleTabChange(value: string) {
    const params = new URLSearchParams(searchParams.toString())
    params.set("tab", value)
    router.replace(`/settings?${params.toString()}`, { scroll: false })
  }

  if (visibleTabs.length === 0) {
    return <p className="text-sm text-muted-foreground">You don&apos;t have access to any settings.</p>
  }

  return (
    <Tabs value={activeTab} onValueChange={handleTabChange}>
      <TabsList className="flex-wrap">
        {visibleTabs.map((tab) => (
          <TabsTrigger key={tab.value} value={tab.value}>
            {tab.label}
          </TabsTrigger>
        ))}
      </TabsList>

      {visibleTabs.map((tab) => (
        <TabsContent key={tab.value} value={tab.value} className="pt-4">
          <tab.Component />
        </TabsContent>
      ))}
    </Tabs>
  )
}

export { SettingsView }
