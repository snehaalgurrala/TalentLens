"use client"

import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { DashboardErrorState } from "@/features/dashboard"
import { useRevokeSession, useSessions } from "@/hooks"
import type { UserSession } from "@/types"

function formatSessionLabel(session: UserSession): string {
  return session.device_label ?? session.user_agent ?? "Unknown device"
}

function ActiveSessionsCard() {
  const { data: sessions, isPending, isError, error, refetch } = useSessions()
  const revokeSession = useRevokeSession()

  async function handleRevoke(sessionId: string) {
    try {
      await revokeSession.mutateAsync(sessionId)
      toast.success("Session revoked")
    } catch (err) {
      const message = err instanceof Error ? err.message : "Something went wrong"
      toast.error(message)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Active Sessions</CardTitle>
        <CardDescription>Devices and browsers currently signed in to your account.</CardDescription>
      </CardHeader>
      <CardContent>
        {isPending && <Skeleton className="h-40 w-full" />}
        {isError && <DashboardErrorState error={error} onRetry={() => void refetch()} />}
        {!isPending && !isError && sessions.length === 0 && (
          <p className="text-sm text-muted-foreground">No active sessions found.</p>
        )}
        {!isPending && !isError && sessions.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Device</TableHead>
                <TableHead>IP Address</TableHead>
                <TableHead>Last Active</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sessions.map((session) => (
                <TableRow key={session.id}>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span>{formatSessionLabel(session)}</span>
                      {session.is_current && <Badge variant="active">This device</Badge>}
                    </div>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {session.ip_address ?? "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(session.last_seen_at).toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={session.is_current}
                      isLoading={
                        revokeSession.isPending && revokeSession.variables === session.id
                      }
                      onClick={() => void handleRevoke(session.id)}
                    >
                      Revoke
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}

export { ActiveSessionsCard }
