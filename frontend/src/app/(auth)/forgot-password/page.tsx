import type { Metadata } from "next"

import { Card, CardContent } from "@/components/ui/card"
import { ForgotPasswordForm } from "@/features/auth/forgot-password-form"

export const metadata: Metadata = { title: "Forgot password" }

export default function ForgotPasswordPage() {
  return (
    <Card>
      <CardContent>
        <ForgotPasswordForm />
      </CardContent>
    </Card>
  )
}
