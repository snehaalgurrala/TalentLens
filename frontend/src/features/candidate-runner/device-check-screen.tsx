"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { CheckCircle2, Loader2, Mic, Monitor, Volume2, Wifi, XCircle } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAssessmentRunner } from "./assessment-runner-context"
import { AssessmentScreenShell } from "./assessment-screen-shell"
import type { DeviceCheckKey } from "./types"

interface CheckRowConfig {
  key: DeviceCheckKey
  label: string
  icon: React.ComponentType<{ className?: string }>
  auto: boolean
  actionLabel?: string
}

const CHECKS: CheckRowConfig[] = [
  { key: "browser", label: "Browser Supported", icon: Monitor, auto: true },
  { key: "internet", label: "Internet Available", icon: Wifi, auto: true },
  { key: "speaker", label: "Speaker Test", icon: Volume2, auto: false, actionLabel: "Test Speakers" },
  { key: "microphone", label: "Microphone Ready", icon: Mic, auto: false, actionLabel: "Enable Microphone" },
]

function CheckRow({ config }: { config: CheckRowConfig }) {
  const { deviceCheck, setDeviceCheckPassed } = useAssessmentRunner()
  const [checking, setChecking] = React.useState(false)
  const passed = deviceCheck[config.key]
  const Icon = config.icon

  const runCheck = React.useCallback(() => {
    setChecking(true)
    const timeout = setTimeout(() => {
      setChecking(false)
      setDeviceCheckPassed(config.key, true)
    }, 900)
    return () => clearTimeout(timeout)
  }, [config.key, setDeviceCheckPassed])

  React.useEffect(() => {
    if (config.auto && !passed) {
      return runCheck()
    }
  }, [config.auto, passed, runCheck])

  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-border px-4 py-3">
      <div className="flex items-center gap-2.5">
        <Icon className="size-4 text-muted-foreground" />
        <span className="text-sm font-medium text-foreground">{config.label}</span>
      </div>
      <div className="flex items-center gap-2">
        {checking && (
          <Loader2 className="size-4 animate-spin text-muted-foreground" aria-hidden="true" />
        )}
        {!checking && passed && (
          <span className="flex items-center gap-1 text-caption font-medium text-success-emphasis">
            <CheckCircle2 className="size-4" aria-hidden="true" /> Ready
          </span>
        )}
        {!checking && !passed && !config.auto && (
          <Button size="sm" variant="outline" onClick={runCheck}>
            {config.actionLabel}
          </Button>
        )}
        {!checking && !passed && config.auto && (
          <span className="flex items-center gap-1 text-caption font-medium text-destructive-emphasis">
            <XCircle className="size-4" aria-hidden="true" /> Not ready
          </span>
        )}
      </div>
    </div>
  )
}

function DeviceCheckScreen() {
  const router = useRouter()
  const { allDeviceChecksPassed } = useAssessmentRunner()

  return (
    <AssessmentScreenShell>
      <Card>
        <CardHeader>
          <CardTitle>Device Check</CardTitle>
          <CardDescription>
            We&apos;ll quickly confirm your device is ready before you begin.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {CHECKS.map((config) => (
            <CheckRow key={config.key} config={config} />
          ))}
          <Button
            size="lg"
            className="mt-2 w-full"
            disabled={!allDeviceChecksPassed}
            onClick={() => router.push("/assessment/instructions")}
          >
            Continue
          </Button>
        </CardContent>
      </Card>
    </AssessmentScreenShell>
  )
}

export { DeviceCheckScreen }
