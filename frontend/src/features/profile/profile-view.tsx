"use client"

import { Skeleton } from "@/components/ui/skeleton"
import { useCurrentUser } from "@/hooks"

import { AccountInfoCard } from "./account-info-card"
import { ChangePasswordForm } from "./change-password-form"
import { ProfileForm } from "./profile-form"

function ProfileView() {
  const { user, isLoading } = useCurrentUser()

  if (isLoading || !user) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-56 w-full" />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <AccountInfoCard user={user} />
      <ProfileForm user={user} />
      <ChangePasswordForm />
    </div>
  )
}

export { ProfileView }
