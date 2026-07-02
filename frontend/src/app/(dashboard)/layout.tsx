import type { ReactNode } from "react"

import { ProtectedShell } from "@/layouts/protected-shell"

export default function DashboardRouteLayout({ children }: { children: ReactNode }) {
  return <ProtectedShell>{children}</ProtectedShell>
}
