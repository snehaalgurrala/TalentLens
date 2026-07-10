/**
 * Raw brand hex values, mirrored from the HSL CSS custom properties in
 * `src/app/globals.css`. Components should use Tailwind utilities
 * (`bg-primary`, `text-success`, etc.) wherever possible — this file exists
 * only for consumers that need a literal color value instead of a CSS
 * variable, namely Recharts (SVG fill/stroke can't resolve `dark:` variants)
 * and any inline-style edge cases.
 *
 * If brand colors change, update both this file and globals.css — the two
 * are intentionally kept in sync rather than one deriving from the other.
 *
 * Every hue below is one of the 3 colors sampled from the TalentSmart logo
 * — Blue #1B5EA3 (main), Green #1D4A28 (secondary), Orange (third, split
 * into #A8500D/#A8390A for AA contrast at different roles) — plus neutral
 * gray/white/black for background/border/text. There is no red in the
 * source palette, so `destructive` reuses the darker end of the orange
 * gradient instead. `accentPurple` keeps its historical name (many
 * components already reference `bg-accent-purple`) but is now the logo's
 * orange, not purple — see globals.css for the per-token contrast notes
 * (WCAG AA: 4.5:1 text, 3:1 UI components).
 */

export const brandColors = {
  primary: "#1B5EA3",
  secondary: "#1D4A28",
  accentPurple: "#A8500D",
  success: "#1D4A28",
  warning: "#F5A623",
  destructive: "#A8390A",
  background: "#FAFAFA",
  surface: "#FFFFFF",
  textPrimary: "#1A1A1A",
  textSecondary: "#6B6B6B",
  border: "#E0E0E0",
} as const;

/**
 * Dark-mode counterparts, contrast-adjusted (lightened) from the light-mode
 * hues so they remain legible against a dark background — not literal
 * reuses of the light-mode hex. Directionally verified against WCAG AA the
 * same way as the light-mode set (see globals.css); primary/secondary/
 * accentPurple share the same known limitation documented there (fill role
 * prioritized over small-text role).
 */
export const brandColorsDark = {
  primary: "#2C7BC9",
  secondary: "#2E7A44",
  accentPurple: "#A85610",
  success: "#2E7A44",
  warning: "#F5A623",
  destructive: "#C24A12",
  background: "#0F0F0F",
  surface: "#1A1A1A",
  textPrimary: "#F2F2F2",
  textSecondary: "#A8A8A8",
  border: "#292929",
} as const;

export type BrandColorKey = keyof typeof brandColors;
