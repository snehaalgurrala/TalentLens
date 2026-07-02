/**
 * Elevation scale. Mirrors the `--shadow-elevation-*` theme tokens in
 * globals.css (`shadow-elevation-1` ... `shadow-elevation-4` utilities).
 * Brand-tinted with the text-primary navy instead of pure black for a
 * softer, more premium feel (Linear/Vercel-style).
 */
export const elevation = {
  1: "0 1px 2px 0 rgb(31 41 55 / 0.06)",
  2: "0 2px 8px -2px rgb(31 41 55 / 0.1), 0 1px 2px -1px rgb(31 41 55 / 0.06)",
  3: "0 8px 24px -4px rgb(31 41 55 / 0.12), 0 2px 6px -2px rgb(31 41 55 / 0.06)",
  4: "0 16px 40px -8px rgb(31 41 55 / 0.16), 0 4px 10px -2px rgb(31 41 55 / 0.08)",
} as const;

export type ElevationKey = keyof typeof elevation;
