"use client"

import * as React from "react"

import type { Organization } from "@/types"

interface OrganizationStoreValue {
  organization: Organization | null
  setOrganization: (organization: Organization | null) => void
  clearOrganization: () => void
}

const OrganizationStoreContext = React.createContext<OrganizationStoreValue | null>(null)

function OrganizationStoreProvider({ children }: { children: React.ReactNode }) {
  const [organization, setOrganization] = React.useState<Organization | null>(null)

  const value = React.useMemo(
    () => ({ organization, setOrganization, clearOrganization: () => setOrganization(null) }),
    [organization]
  )

  return (
    <OrganizationStoreContext.Provider value={value}>
      {children}
    </OrganizationStoreContext.Provider>
  )
}

function useOrganizationStore(): OrganizationStoreValue {
  const ctx = React.useContext(OrganizationStoreContext)
  if (!ctx) {
    throw new Error("useOrganizationStore must be used within an OrganizationStoreProvider")
  }
  return ctx
}

export { OrganizationStoreProvider, useOrganizationStore }
