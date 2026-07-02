import type { CSSProperties } from "react"

import { brandColors, brandColorsDark } from "@/design-system/tokens/colors"

/** Ordered series palette for multi-series charts (bar/line/pie). */
export const chartPalette = [
  brandColors.primaryBlue,
  brandColors.secondaryBlue,
  brandColors.greenAccent,
  brandColors.deepPurple,
] as const

export const chartPaletteDark = [
  brandColorsDark.primaryBlue,
  brandColorsDark.secondaryBlue,
  brandColorsDark.greenAccent,
  brandColorsDark.deepPurple,
] as const

export interface ChartDefaults {
  grid: { stroke: string; strokeDasharray: string }
  axis: { stroke: string; fontSize: number; fontFamily: string }
  tooltip: {
    contentStyle: CSSProperties
    labelStyle: CSSProperties
  }
}

function buildDefaults(colors: Record<keyof typeof brandColors, string>): ChartDefaults {
  return {
    grid: { stroke: colors.border, strokeDasharray: "3 3" },
    axis: {
      stroke: colors.textSecondary,
      fontSize: 12,
      fontFamily: "var(--font-inter), system-ui, sans-serif",
    },
    tooltip: {
      contentStyle: {
        backgroundColor: colors.surface,
        border: `1px solid ${colors.border}`,
        borderRadius: 8,
        fontSize: 13,
        color: colors.textPrimary,
      },
      labelStyle: { color: colors.textSecondary, fontWeight: 500 },
    },
  }
}

export const chartDefaults = buildDefaults(brandColors)
export const chartDefaultsDark = buildDefaults(brandColorsDark)
