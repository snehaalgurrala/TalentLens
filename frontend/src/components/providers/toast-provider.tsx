"use client"

import { Toaster } from "@/components/ui/sonner"

function ToastProvider() {
  return <Toaster position="top-right" richColors closeButton />
}

export { ToastProvider }
