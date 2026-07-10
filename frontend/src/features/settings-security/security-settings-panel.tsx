"use client"

import { ChangePasswordForm } from "@/features/profile"

import { ActiveSessionsCard } from "./active-sessions-card"
import { FutureSecurityCard } from "./future-security-card"
import { RevokeOtherSessionsCard } from "./revoke-other-sessions-card"

function SecuritySettingsPanel() {
  return (
    <div className="flex flex-col gap-6">
      <ChangePasswordForm />
      <ActiveSessionsCard />
      <RevokeOtherSessionsCard />
      <FutureSecurityCard />
    </div>
  )
}

export { SecuritySettingsPanel }
