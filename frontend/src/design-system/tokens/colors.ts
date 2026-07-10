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
 * Every value below derives from exactly 4 hues taken from the TalentSmart
 * logo — no other hue appears anywhere in this palette:
 *   Blue #1B5EA3 (wordmark) · Amber #F5A623 / Deep Orange #A8390A (swoosh
 *   gradient, split into two shades for AA contrast) · Navy-Purple #2A1B4D
 *   (swoosh) · Gray #7A7A7A ("smart" wordmark). There is no green or red in
 *   the source palette, so `success` reuses a deeper blue and `destructive`
 *   reuses the swoosh's darker orange instead — see globals.css for the
 *   per-token contrast notes (WCAG AA: 4.5:1 text, 3:1 UI components).
 */

export const brandColors = {
  primary: "#1B5EA3",
  secondary: "#2A1B4D",
  accentPurple: "#2A1B4D",
  success: "#124676",
  warning: "#F5A623",
  destructive: "#A8390A",
  background: "#FAFAFA",
  surface: "#FFFFFF",
  textPrimary: "#150F22",
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
  secondary: "#4A3A78",
  accentPurple: "#6A4FA0",
  success: "#1F6BB5",
  warning: "#F5A623",
  destructive: "#C24A12",
  background: "#0A0712",
  surface: "#150F22",
  textPrimary: "#F2F2F2",
  textSecondary: "#A8A8A8",
  border: "#201933",
} as const;

export type BrandColorKey = keyof typeof brandColors;
