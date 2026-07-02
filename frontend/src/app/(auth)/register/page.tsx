import type { Metadata } from "next"
import Link from "next/link"
import { redirect } from "next/navigation"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export const metadata: Metadata = { title: "Create account" }

interface RegisterPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}

/**
 * Registration always requires an invitation (backend has no self-serve
 * signup) — this page just forwards a token straight into the real flow at
 * /invite, or explains why registration needs an invite when there isn't one.
 */
export default async function RegisterPage({ searchParams }: RegisterPageProps) {
  const params = await searchParams

  if (typeof params.token === "string" && params.token) {
    const query = new URLSearchParams()
    for (const [key, value] of Object.entries(params)) {
      if (typeof value === "string") query.set(key, value)
    }
    redirect(`/invite?${query.toString()}`)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create account</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 text-sm text-muted-foreground">
        <p>
          You need an invitation to create a TalentSmart account. Check your email for an
          invite link from your organization administrator.
        </p>
        <Button asChild className="w-full">
          <Link href="/login">Back to login</Link>
        </Button>
      </CardContent>
    </Card>
  )
}
