import type { CSSProperties } from "react"

import { brandColors, brandColorsDark } from "@/design-system/tokens/colors"

/**
 * Ordered series palette for multi-series charts (bar/line/pie). Uses the
 * brand's 3 real hue families — blue, green, orange — plus mid-gray as a
 * deliberately muted 4th/"other" series (a standard categorical-plus-
 * neutral pattern). `secondary` and `success` share one hex (both = green,
 * see colors.ts), so this pulls `secondary` rather than listing the same
 * green twice.
 */
export const chartPalette = [
  brandColors.primary,
  brandColors.secondary,
  brandColors.warning,
  "#7A7A7A",
] as const

export const chartPaletteDark = [
  brandColorsDark.primary,
  brandColorsDark.secondary,
  brandColorsDark.warning,
  "#A8A8A8",
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
