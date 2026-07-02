"use client"

import * as React from "react"
import { useRouter } from "next/navigation"

import { Skeleton } from "@/components/ui/skeleton"
import { DEFAULT_LOGIN_ROUTE } from "@/lib/constants"
import { useAuth } from "@/hooks/use-auth"
import { MainLayout } from "@/layouts/main-layout"

/**
 * Client-side route guard for the (dashboard) route group. Middleware already
 * redirects anonymous requests at the edge using the session marker cookie;
 * this is the second, authoritative check once the real session has been
 * verified against the API (session bootstrap / token refresh).
 */
function ProtectedShell({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const { isAuthenticated, isInitializing } = useAuth()

  React.useEffect(() => {
    if (!isInitializing && !isAuthenticated) {
      router.replace(DEFAULT_LOGIN_ROUTE)
    }
  }, [isInitializing, isAuthenticated, router])

  if (isInitializing || !isAuthenticated) {
    return (
      <div className="flex h-dvh w-full items-center justify-center bg-background">
        <Skeleton className="h-8 w-8 rounded-full" />
      </div>
    )
  }

  return <MainLayout>{children}</MainLayout>
}

export { ProtectedShell }
