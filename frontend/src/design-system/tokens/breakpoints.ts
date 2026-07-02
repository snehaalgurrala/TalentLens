/**
 * Breakpoint scale. Mirrors Tailwind v4's default `screens` (sm/md/lg/xl/2xl)
 * so JS-side consumers (media query hooks, Recharts ResponsiveContainer
 * logic) share the same thresholds as the CSS utilities instead of
 * hardcoding pixel values separately.
 */
export const breakpoints = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  "2xl": 1536,
} as const;

export type BreakpointKey = keyof typeof breakpoints;
