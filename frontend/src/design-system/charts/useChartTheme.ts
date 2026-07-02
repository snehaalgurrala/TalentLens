"use client"

import { useTheme } from "next-themes"

import {
  chartDefaults,
  chartDefaultsDark,
  chartPalette,
  chartPaletteDark,
} from "@/design-system/charts/chart-theme"

/**
 * Resolves the active next-themes theme to the matching Recharts palette and
 * default style objects, so chart consumers don't re-derive colors per theme.
 */
export function useChartTheme() {
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === "dark"

  return {
    palette: isDark ? chartPaletteDark : chartPalette,
    defaults: isDark ? chartDefaultsDark : chartDefaults,
  }
}
