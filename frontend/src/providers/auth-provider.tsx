"use client"

import * as React from "react"
import { useRouter } from "next/navigation"

import { DEFAULT_LOGIN_ROUTE } from "@/lib/constants"
import {
  clearSession,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
  setSessionCookie,
} from "@/lib/storage"
import { registerAuthFailureHandler, setupInterceptors } from "@/services/interceptors"
import { authService } from "@/services/auth.service"
import { AuthStoreProvider, useAuthStore } from "@/store/auth-store"
import { OrganizationStoreProvider, useOrganizationStore } from "@/store/organization-store"
import { UserStoreProvider, useUserStore } from "@/store/user-store"
import type { LoginRequest, RegisterRequest, TokenResponse, User } from "@/types"

setupInterceptors()

interface AuthContextValue {
  login: (data: LoginRequest, remember?: boolean) => Promise<User>
  register: (data: RegisterRequest) => Promise<User>
  logout: () => void
}

const AuthContext = React.createContext<AuthContextValue | null>(null)

function applyTokens(tokens: TokenResponse, remember?: boolean): void {
  setAccessToken(tokens.access_token)
  setRefreshToken(tokens.refresh_token, remember)
  setSessionCookie(true)
}

function AuthBootstrap({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const { setStatus } = useAuthStore()
  const { setUser, clearUser } = useUserStore()
  const { clearOrganization } = useOrganizationStore()

  const handleAuthFailure = React.useCallback(() => {
    clearUser()
    clearOrganization()
    setStatus("unauthenticated")
    router.push(`${DEFAULT_LOGIN_ROUTE}?session_expired=1`)
  }, [clearUser, clearOrganization, setStatus, router])

  React.useEffect(() => {
    registerAuthFailureHandler(handleAuthFailure)
  }, [handleAuthFailure])

  React.useEffect(() => {
    let cancelled = false

    async function bootstrap() {
      const refreshToken = getRefreshToken()
      if (!refreshToken) {
        setStatus("unauthenticated")
        return
      }

      setStatus("authenticating")
      try {
        const tokens = await authService.refresh(refreshToken)
        if (cancelled) return
        applyTokens(tokens)

        const user = await authService.getCurrentUser()
        if (cancelled) return
        setUser(user)
        setStatus("authenticated")
      } catch {
        if (cancelled) return
        clearSession()
        clearUser()
        clearOrganization()
        setStatus("unauthenticated")
      }
    }

    bootstrap()
    return () => {
      cancelled = true
    }
    // Runs once on mount to restore a persisted session.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const login = React.useCallback(
    async (data: LoginRequest, remember?: boolean) => {
      const tokens = await authService.login(data)
      applyTokens(tokens, remember)
      const user = await authService.getCurrentUser()
      setUser(user)
      setStatus("authenticated")
      return user
    },
    [setUser, setStatus]
  )

  const register = React.useCallback(
    async (data: RegisterRequest) => {
      const tokens = await authService.register(data)
      applyTokens(tokens)
      const user = await authService.getCurrentUser()
      setUser(user)
      setStatus("authenticated")
      return user
    },
    [setUser, setStatus]
  )

  const logout = React.useCallback(() => {
    clearSession()
    clearUser()
    clearOrganization()
    setStatus("unauthenticated")
    router.push(DEFAULT_LOGIN_ROUTE)
  }, [clearUser, clearOrganization, setStatus, router])

  const value = React.useMemo(() => ({ login, register, logout }), [login, register, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

function AuthProvider({ children }: { children: React.ReactNode }) {
  return (
    <AuthStoreProvider>
      <UserStoreProvider>
        <OrganizationStoreProvider>
          <AuthBootstrap>{children}</AuthBootstrap>
        </OrganizationStoreProvider>
      </UserStoreProvider>
    </AuthStoreProvider>
  )
}

function useAuthActions(): AuthContextValue {
  const ctx = React.useContext(AuthContext)
  if (!ctx) {
    throw new Error("useAuthActions must be used within an AuthProvider")
  }
  return ctx
}

export { AuthProvider, useAuthActions }
