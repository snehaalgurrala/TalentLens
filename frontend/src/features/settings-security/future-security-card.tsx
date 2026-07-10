"use client"

import { KeyRound, ShieldCheck } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { FEATURES } from "@/config/features"

function FutureSecurityCard() {
  return (
    <Card className="opacity-75">
      <CardHeader>
        <CardTitle>More Security Controls</CardTitle>
        <CardDescription>Planned for a future release.</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between rounded-lg border border-dashed border-border px-3 py-2.5">
            <div className="flex items-center gap-2">
              <ShieldCheck className="size-4 text-muted-foreground" aria-hidden="true" />
              <span className="text-sm font-medium">Two-Factor Authentication</span>
            </div>
            <Badge variant="outline">{FEATURES.mfaEnabled ? "Enabled" : "Coming soon"}</Badge>
          </div>
          <div className="flex items-center justify-between rounded-lg border border-dashed border-border px-3 py-2.5">
            <div className="flex items-center gap-2">
              <KeyRound className="size-4 text-muted-foreground" aria-hidden="true" />
              <span className="text-sm font-medium">API Keys</span>
            </div>
            <Badge variant="outline">Coming soon</Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export { FutureSecurityCard }
