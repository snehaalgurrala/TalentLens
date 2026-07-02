import * as React from "react"

import { AppHeader } from "@/layouts/app-header"
import { AppSidebar } from "@/layouts/app-sidebar"
import { ContentArea } from "@/layouts/content-area"
import { MobileDrawer } from "@/layouts/mobile-drawer"

/** The authenticated app shell — sidebar + header + scrollable content, with a mobile drawer fallback. */
function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-dvh w-full overflow-hidden bg-background">
      <AppSidebar />
      <MobileDrawer />
      <div className="flex min-w-0 flex-1 flex-col">
        <AppHeader />
        <ContentArea>{children}</ContentArea>
      </div>
    </div>
  )
}

export { MainLayout }
