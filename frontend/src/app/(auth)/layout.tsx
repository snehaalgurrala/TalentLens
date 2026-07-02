import type { ReactNode } from "react"
import { Suspense } from "react"

import { AuthLayout } from "@/layouts/auth-layout"
import { SessionExpiredDialog } from "@/layouts/session-expired-dialog"

export default function AuthRouteLayout({ children }: { children: ReactNode }) {
  return (
    <AuthLayout>
      {children}
      <Suspense fallback={null}>
        <SessionExpiredDialog />
      </Suspense>
    </AuthLayout>
  )
}
