"use client"

import * as React from "react"

import type { User } from "@/types"

interface UserStoreValue {
  user: User | null
  setUser: (user: User | null) => void
  clearUser: () => void
}

const UserStoreContext = React.createContext<UserStoreValue | null>(null)

function UserStoreProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<User | null>(null)

  const value = React.useMemo(
    () => ({ user, setUser, clearUser: () => setUser(null) }),
    [user]
  )

  return <UserStoreContext.Provider value={value}>{children}</UserStoreContext.Provider>
}

function useUserStore(): UserStoreValue {
  const ctx = React.useContext(UserStoreContext)
  if (!ctx) {
    throw new Error("useUserStore must be used within a UserStoreProvider")
  }
  return ctx
}

export { UserStoreProvider, useUserStore }
