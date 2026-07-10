"use client"

import * as React from "react"
import { UserPlus } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { TableLoadingState } from "@/components/ui/table-loading-state"
import { ROLE_LABELS } from "@/config/permissions"
import { DashboardErrorState } from "@/features/dashboard"
import { useCurrentUser, useOrgUsers } from "@/hooks"
import { formatDate } from "@/utils"

import { InviteUserDialog } from "./invite-user-dialog"
import { UserActionsMenu } from "./user-actions-menu"

const COLUMN_COUNT = 6

function UserManagementPanel() {
  const [inviteOpen, setInviteOpen] = React.useState(false)
  const { data, isLoading, isError, error, refetch } = useOrgUsers()
  const { user: currentUser } = useCurrentUser()

  const users = data ?? []

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-2">
        <div className="flex flex-col gap-1">
          <CardTitle>User Management</CardTitle>
          <CardDescription>Manage who has access to your organization.</CardDescription>
        </div>
        <Button type="button" onClick={() => setInviteOpen(true)}>
          <UserPlus aria-hidden="true" />
          Invite User
        </Button>
      </CardHeader>
      <CardContent>
        {isError ? (
          <DashboardErrorState error={error} onRetry={() => void refetch()} />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Joined</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableLoadingState columns={COLUMN_COUNT} />
              ) : users.length === 0 ? (
                <TableRow className="hover:bg-transparent">
                  <TableCell colSpan={COLUMN_COUNT}>
                    <TableEmptyState title="No users yet" description="Invite your first team member to get started." />
                  </TableCell>
                </TableRow>
              ) : (
                users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell className="font-medium text-foreground">{user.full_name}</TableCell>
                    <TableCell className="text-muted-foreground">{user.email}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">{ROLE_LABELS[user.role]}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={user.is_active ? "active" : "rejected"}>
                        {user.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell>{formatDate(user.created_at)}</TableCell>
                    <TableCell className="text-right">
                      {currentUser?.id === user.id ? (
                        <span className="text-xs text-muted-foreground">You</span>
                      ) : (
                        <UserActionsMenu user={user} callerRole={currentUser?.role ?? null} />
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        )}
      </CardContent>

      <InviteUserDialog open={inviteOpen} onOpenChange={setInviteOpen} onInvited={() => void refetch()} />
    </Card>
  )
}

export { UserManagementPanel }
