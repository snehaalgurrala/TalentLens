"use client"

import * as React from "react"
import { useTheme } from "next-themes"
import { Monitor, Moon, Sun } from "lucide-react"

import { Button } from "@/components/ui/button"

const options = [
  { value: "light", icon: Sun, label: "Light theme" },
  { value: "dark", icon: Moon, label: "Dark theme" },
  { value: "system", icon: Monitor, label: "System theme" },
] as const

function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)

  React.useEffect(() => setMounted(true), [])

  return (
    <div className="inline-flex items-center gap-0.5 rounded-lg border border-border bg-surface p-0.5">
      {options.map(({ value, icon: Icon, label }) => (
        <Button
          key={value}
          type="button"
          variant={mounted && theme === value ? "secondary" : "ghost"}
          size="icon-sm"
          aria-label={label}
          aria-pressed={mounted && theme === value}
          onClick={() => setTheme(value)}
        >
          <Icon className="size-4" aria-hidden="true" />
        </Button>
      ))}
    </div>
  )
}

export { ThemeToggle }
