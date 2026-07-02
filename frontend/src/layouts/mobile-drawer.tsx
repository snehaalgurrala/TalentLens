"use client"

import * as React from "react"
import Link from "next/link"
import { AnimatePresence, motion } from "framer-motion"
import { Dialog as DialogPrimitive } from "radix-ui"
import { XIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { fadeVariants } from "@/design-system/motion/variants"
import { drawerLeftVariants } from "@/design-system/motion/drawer-variants"
import { siteConfig } from "@/config/site"
import { useSidebar } from "@/hooks/use-sidebar"
import { NavList } from "@/layouts/nav-list"

function MobileDrawer() {
  const { mobileOpen, setMobileOpen } = useSidebar()

  return (
    <DialogPrimitive.Root open={mobileOpen} onOpenChange={setMobileOpen}>
      <AnimatePresence>
        {mobileOpen && (
          <DialogPrimitive.Portal forceMount>
            <DialogPrimitive.Overlay asChild forceMount>
              <motion.div
                className="fixed inset-0 z-(--z-drawer) bg-black/40 lg:hidden"
                initial="hidden"
                animate="visible"
                exit="exit"
                variants={fadeVariants}
              />
            </DialogPrimitive.Overlay>
            <DialogPrimitive.Content asChild forceMount aria-describedby={undefined}>
              <motion.div
                className={cn(
                  "fixed inset-y-0 left-0 z-(--z-drawer) flex w-72 max-w-[85vw] flex-col border-r border-border bg-surface p-2 outline-none lg:hidden"
                )}
                initial="hidden"
                animate="visible"
                exit="exit"
                variants={drawerLeftVariants}
              >
                <div className="flex h-12 shrink-0 items-center justify-between px-2">
                  <DialogPrimitive.Title asChild>
                    <Link
                      href="/dashboard"
                      onClick={() => setMobileOpen(false)}
                      className="flex items-center gap-2 text-sm font-semibold text-foreground"
                    >
                      <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary text-xs text-primary-foreground">
                        {siteConfig.name.charAt(0)}
                      </span>
                      {siteConfig.name}
                    </Link>
                  </DialogPrimitive.Title>
                  <DialogPrimitive.Close asChild>
                    <Button variant="ghost" size="icon-sm" aria-label="Close navigation">
                      <XIcon aria-hidden="true" />
                    </Button>
                  </DialogPrimitive.Close>
                </div>
                <nav className="flex-1 overflow-y-auto p-2">
                  <NavList onNavigate={() => setMobileOpen(false)} />
                </nav>
              </motion.div>
            </DialogPrimitive.Content>
          </DialogPrimitive.Portal>
        )}
      </AnimatePresence>
    </DialogPrimitive.Root>
  )
}

export { MobileDrawer }
