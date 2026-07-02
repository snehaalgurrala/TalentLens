import type { Metadata } from "next"
import { Suspense } from "react"

import { Card, CardContent } from "@/components/ui/card"
import { LoginForm } from "@/features/auth/login-form"

export const metadata: Metadata = { title: "Log in" }

export default function LoginPage() {
  return (
    <Card>
      <CardContent>
        <Suspense fallback={null}>
          <LoginForm />
        </Suspense>
      </CardContent>
    </Card>
  )
}
