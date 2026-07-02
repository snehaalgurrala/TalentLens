"use client"

import * as React from "react"

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"

interface OpenModalOptions {
  title?: string
  description?: string
  content: React.ReactNode
  onClose?: () => void
}

interface ModalContextValue {
  openModal: (options: OpenModalOptions) => void
  closeModal: () => void
}

const ModalContext = React.createContext<ModalContextValue | null>(null)

function ModalProvider({ children }: { children: React.ReactNode }) {
  const [modal, setModal] = React.useState<OpenModalOptions | null>(null)

  const closeModal = React.useCallback(() => {
    modal?.onClose?.()
    setModal(null)
  }, [modal])

  const openModal = React.useCallback((options: OpenModalOptions) => {
    setModal(options)
  }, [])

  const value = React.useMemo(() => ({ openModal, closeModal }), [openModal, closeModal])

  return (
    <ModalContext.Provider value={value}>
      {children}
      <Dialog open={modal !== null} onOpenChange={(open) => !open && closeModal()}>
        <DialogContent>
          {(modal?.title || modal?.description) && (
            <DialogHeader>
              {modal?.title && <DialogTitle>{modal.title}</DialogTitle>}
              {modal?.description && <DialogDescription>{modal.description}</DialogDescription>}
            </DialogHeader>
          )}
          {modal?.content}
        </DialogContent>
      </Dialog>
    </ModalContext.Provider>
  )
}

function useModal(): ModalContextValue {
  const ctx = React.useContext(ModalContext)
  if (!ctx) {
    throw new Error("useModal must be used within a ModalProvider")
  }
  return ctx
}

export { ModalProvider, useModal }
