/**
 * Semantic spacing scale for component props (Stack/Grid `gap`, etc).
 * Tailwind v4's own spacing scale (`p-4`, `gap-2`, ...) stays the default
 * `--spacing` multiplier and is used directly for one-off utilities — this
 * scale exists for components that expose a constrained `gap`/`padding`
 * prop instead of raw Tailwind classes.
 */
export const spacing = {
  none: "0",
  xs: "0.5rem",
  sm: "0.75rem",
  md: "1rem",
  lg: "1.5rem",
  xl: "2rem",
  "2xl": "3rem",
  "3xl": "4rem",
} as const;

export type SpacingKey = keyof typeof spacing;
