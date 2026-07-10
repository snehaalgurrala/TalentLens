import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ROLE_LABELS } from "@/config/permissions"
import { FEATURES } from "@/config/features"
import type { User } from "@/types"

export interface AccountInfoCardProps {
  user: User
}

function initials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/)
  return parts
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("")
}

function AccountInfoCard({ user }: AccountInfoCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Account</CardTitle>
        <CardDescription>Read-only account details.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <Avatar className="size-14">
            <AvatarFallback>{initials(user.full_name)}</AvatarFallback>
          </Avatar>
          <div className="flex flex-col gap-1">
            <p className="text-body font-medium text-foreground">{user.full_name}</p>
            {!FEATURES.avatarUploadEnabled && (
              <p className="text-xs text-muted-foreground">Photo upload isn&apos;t available yet.</p>
            )}
          </div>
        </div>

        <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-muted-foreground">Role</dt>
            <dd className="mt-1">
              <Badge variant="secondary">{ROLE_LABELS[user.role]}</Badge>
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Account Status</dt>
            <dd className="mt-1">
              <Badge variant={user.is_active ? "active" : "rejected"}>
                {user.is_active ? "Active" : "Inactive"}
              </Badge>
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Created</dt>
            <dd className="mt-1 text-foreground">
              {new Date(user.created_at).toLocaleDateString()}
            </dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  )
}

export { AccountInfoCard }
