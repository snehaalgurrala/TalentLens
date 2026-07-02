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
 */

export const brandColors = {
  primaryBlue: "#005A9C",
  secondaryBlue: "#1E74B7",
  greenAccent: "#37B34A",
  deepPurple: "#3A1545",
  background: "#F7F9FC",
  surface: "#FFFFFF",
  textPrimary: "#1F2937",
  textSecondary: "#6B7280",
  border: "#E5E7EB",
  destructive: "#DC2828",
  warning: "#F59F0A",
} as const;

/**
 * Dark-mode counterparts, contrast-adjusted (lightened) from the light-mode
 * hues so they remain legible against a dark background — not literal
 * reuses of the light-mode hex. Verified against WCAG AA:
 *  - white text on primaryBlue/secondaryBlue/destructive: >= 4.5:1
 *  - dark text on greenAccent/warning: >= 7:1 (matches the light-mode
 *    pairing, since both fail AA with white text at full saturation)
 */
export const brandColorsDark = {
  primaryBlue: "#0A75C2",
  secondaryBlue: "#1577C1",
  greenAccent: "#4EBC5E",
  deepPurple: "#8E3FA6",
  background: "#0E121B",
  surface: "#171C26",
  textPrimary: "#E7EBEF",
  textSecondary: "#98A4B3",
  border: "#2D3543",
  destructive: "#BD2828",
  warning: "#F0B042",
} as const;

export type BrandColorKey = keyof typeof brandColors;
