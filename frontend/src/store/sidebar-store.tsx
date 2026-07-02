"use client"

import * as React from "react"

const SIDEBAR_STORAGE_KEY = "tl_sidebar_collapsed"

interface SidebarStoreValue {
  collapsed: boolean
  setCollapsed: (collapsed: boolean) => void
  toggleCollapsed: () => void
  mobileOpen: boolean
  setMobileOpen: (open: boolean) => void
}

const SidebarStoreContext = React.createContext<SidebarStoreValue | null>(null)

function SidebarStoreProvider({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsedState] = React.useState(false)
  const [mobileOpen, setMobileOpen] = React.useState(false)

  React.useEffect(() => {
    const stored = window.localStorage.getItem(SIDEBAR_STORAGE_KEY)
    if (stored !== null) setCollapsedState(stored === "true")
  }, [])

  const setCollapsed = React.useCallback((next: boolean) => {
    setCollapsedState(next)
    window.localStorage.setItem(SIDEBAR_STORAGE_KEY, String(next))
  }, [])

  const toggleCollapsed = React.useCallback(() => {
    setCollapsedState((prev) => {
      const next = !prev
      window.localStorage.setItem(SIDEBAR_STORAGE_KEY, String(next))
      return next
    })
  }, [])

  const value = React.useMemo(
    () => ({ collapsed, setCollapsed, toggleCollapsed, mobileOpen, setMobileOpen }),
    [collapsed, setCollapsed, toggleCollapsed, mobileOpen]
  )

  return <SidebarStoreContext.Provider value={value}>{children}</SidebarStoreContext.Provider>
}

function useSidebarStore(): SidebarStoreValue {
  const ctx = React.useContext(SidebarStoreContext)
  if (!ctx) {
    throw new Error("useSidebarStore must be used within a SidebarStoreProvider")
  }
  return ctx
}

export { SidebarStoreProvider, useSidebarStore }
