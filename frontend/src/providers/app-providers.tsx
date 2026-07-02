import * as React from "react"

import { AuthProvider } from "@/providers/auth-provider"
import { LoadingProvider } from "@/providers/loading-provider"
import { ModalProvider } from "@/providers/modal-provider"
import { QueryProvider } from "@/providers/query-provider"
import { NotificationStoreProvider } from "@/store/notification-store"
import { SidebarStoreProvider } from "@/store/sidebar-store"

/**
 * Composes every app-wide provider in one place. Theme and Toast providers
 * live in `components/providers` (design system) and stay in `app/layout.tsx`
 * so styling primitives remain independent of application state.
 */
function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <QueryProvider>
      <AuthProvider>
        <SidebarStoreProvider>
          <NotificationStoreProvider>
            <ModalProvider>
              <LoadingProvider>{children}</LoadingProvider>
            </ModalProvider>
          </NotificationStoreProvider>
        </SidebarStoreProvider>
      </AuthProvider>
    </QueryProvider>
  )
}

export { AppProviders }
