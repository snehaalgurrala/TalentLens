"use client"

import * as React from "react"
import { KeyRound, MoreHorizontal, Power, PowerOff, UserCog } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ROLE_LABELS } from "@/config/permissions"
import {
  useDeactivateUser,
  useReactivateUser,
  useResetUserPassword,
  useUpdateUserRole,
} from "@/hooks"
import type { UserListItem, UserRole } from "@/types"

import { getAssignableRoles } from "./constants"

export interface UserActionsMenuProps {
  user: UserListItem
  callerRole: UserRole | null
}

function UserActionsMenu({ user, callerRole }: UserActionsMenuProps) {
  const [roleDialogOpen, setRoleDialogOpen] = React.useState(false)
  const [selectedRole, setSelectedRole] = React.useState<UserRole>(user.role)
  const [deactivateDialogOpen, setDeactivateDialogOpen] = React.useState(false)
  const [resetPasswordDialogOpen, setResetPasswordDialogOpen] = React.useState(false)
  const [resetToken, setResetToken] = React.useState<string | null>(null)

  const updateRole = useUpdateUserRole()
  const deactivateUser = useDeactivateUser()
  const reactivateUser = useReactivateUser()
  const resetPassword = useResetUserPassword()

  const assignableRoles = getAssignableRoles(callerRole)

  function openRoleDialog() {
    setSelectedRole(user.role)
    setRoleDialogOpen(true)
  }

  function handleUpdateRole() {
    updateRole.mutate(
      { userId: user.id, role: selectedRole },
      {
        onSuccess: () => {
          toast.success(`${user.full_name}'s role updated to ${ROLE_LABELS[selectedRole]}`)
          setRoleDialogOpen(false)
        },
        onError: (error) => toast.error(error.message || "Failed to update role"),
      }
    )
  }

  function handleDeactivate() {
    deactivateUser.mutate(user.id, {
      onSuccess: () => {
        toast.success(`${user.full_name} deactivated`)
        setDeactivateDialogOpen(false)
      },
      onError: (error) => {
        toast.error(error.message || "Failed to deactivate user")
        setDeactivateDialogOpen(false)
      },
    })
  }

  function handleReactivate() {
    reactivateUser.mutate(user.id, {
      onSuccess: () => toast.success(`${user.full_name} reactivated`),
      onError: (error) => toast.error(error.message || "Failed to reactivate user"),
    })
  }

  function openResetPasswordDialog() {
    setResetToken(null)
    setResetPasswordDialogOpen(true)
    resetPassword.mutate(user.id, {
      onSuccess: (result) => setResetToken(result.token),
      onError: (error) => {
        toast.error(error.message || "Failed to reset password")
        setResetPasswordDialogOpen(false)
      },
    })
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon-sm" aria-label={`Actions for ${user.full_name}`}>
            <MoreHorizontal className="size-4" aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onSelect={openRoleDialog}>
            <UserCog aria-hidden="true" />
            Change Role
          </DropdownMenuItem>
          {user.is_active ? (
            <DropdownMenuItem variant="destructive" onSelect={() => setDeactivateDialogOpen(true)}>
              <PowerOff aria-hidden="true" />
              Deactivate
            </DropdownMenuItem>
          ) : (
            <DropdownMenuItem onSelect={handleReactivate} disabled={reactivateUser.isPending}>
              <Power aria-hidden="true" />
              Reactivate
            </DropdownMenuItem>
          )}
          <DropdownMenuItem onSelect={openResetPasswordDialog}>
            <KeyRound aria-hidden="true" />
            Reset Password
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={roleDialogOpen} onOpenChange={setRoleDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Change role</DialogTitle>
            <DialogDescription>Update {user.full_name}&rsquo;s role in this organization.</DialogDescription>
          </DialogHeader>
          <Select value={selectedRole} onValueChange={(value) => setSelectedRole(value as UserRole)}>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {assignableRoles.map((role) => (
                <SelectItem key={role} value={role}>
                  {ROLE_LABELS[role]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRoleDialogOpen(false)}>
              Cancel
            </Button>
            <Button isLoading={updateRole.isPending} onClick={handleUpdateRole}>
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deactivateDialogOpen} onOpenChange={setDeactivateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Deactivate {user.full_name}?</DialogTitle>
            <DialogDescription>
              They will immediately lose access to this organization. You can reactivate them later.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeactivateDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" isLoading={deactivateUser.isPending} onClick={handleDeactivate}>
              Deactivate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={resetPasswordDialogOpen} onOpenChange={setResetPasswordDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reset password</DialogTitle>
            <DialogDescription>
              A one-time reset token for {user.full_name}. There is no email delivery for this yet — share
              it with them directly. It will not be shown again.
            </DialogDescription>
          </DialogHeader>
          {resetPassword.isPending ? (
            <p className="text-sm text-muted-foreground">Generating token…</p>
          ) : (
            resetToken && (
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="reset-token">Reset Token</Label>
                <div className="flex gap-2">
                  <Input id="reset-token" readOnly value={resetToken} className="font-mono text-xs" />
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      void navigator.clipboard.writeText(resetToken)
                      toast.success("Token copied to clipboard")
                    }}
                  >
                    Copy
                  </Button>
                </div>
              </div>
            )
          )}
          <DialogFooter>
            <Button onClick={() => setResetPasswordDialogOpen(false)}>Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

export { UserActionsMenu }
