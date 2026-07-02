"use client"

import * as React from "react"

export type AuthStatus = "idle" | "authenticating" | "authenticated" | "unauthenticated"

interface AuthStoreValue {
  status: AuthStatus
  setStatus: (status: AuthStatus) => void
}

const AuthStoreContext = React.createContext<AuthStoreValue | null>(null)

function AuthStoreProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = React.useState<AuthStatus>("idle")

  const value = React.useMemo(() => ({ status, setStatus }), [status])

  return <AuthStoreContext.Provider value={value}>{children}</AuthStoreContext.Provider>
}

function useAuthStore(): AuthStoreValue {
  const ctx = React.useContext(AuthStoreContext)
  if (!ctx) {
    throw new Error("useAuthStore must be used within an AuthStoreProvider")
  }
  return ctx
}

export { AuthStoreProvider, useAuthStore }
