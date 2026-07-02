import type { Metadata } from "next"
import Link from "next/link"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { InvitationRegisterForm } from "@/features/auth/invitation-register-form"

export const metadata: Metadata = { title: "Accept invitation" }

interface InvitePageProps {
  searchParams: Promise<{ token?: string; email?: string; org?: string }>
}

export default async function InvitePage({ searchParams }: InvitePageProps) {
  const { token, email, org } = await searchParams

  if (!token || !email) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Invalid invitation link</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 text-sm text-muted-foreground">
          <p>
            This invitation link is missing or malformed. Please use the link from your
            invitation email, or ask your organization admin to send a new one.
          </p>
          <Button asChild className="w-full">
            <Link href="/login">Back to login</Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardContent>
        <InvitationRegisterForm token={token} email={email} orgName={org ?? "your organization"} />
      </CardContent>
    </Card>
  )
}
