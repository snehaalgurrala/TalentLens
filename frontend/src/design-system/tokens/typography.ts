/**
 * Typography scale. Mirrors the `--text-*` theme tokens in globals.css —
 * use Tailwind utilities (`text-display`, `text-h1`, ...) in components;
 * this object is for non-Tailwind consumers (Recharts axis/legend fonts,
 * documentation, tests).
 */

export const fontFamily = {
  sans: "var(--font-inter), system-ui, sans-serif",
} as const;

export interface TypeScaleEntry {
  fontSize: string;
  lineHeight: number;
  fontWeight: number;
  letterSpacing?: string;
}

export const typeScale = {
  display: { fontSize: "3.5rem", lineHeight: 1.1, fontWeight: 700, letterSpacing: "-0.02em" },
  h1: { fontSize: "2.75rem", lineHeight: 1.15, fontWeight: 700, letterSpacing: "-0.02em" },
  h2: { fontSize: "2.25rem", lineHeight: 1.2, fontWeight: 700, letterSpacing: "-0.01em" },
  h3: { fontSize: "1.875rem", lineHeight: 1.25, fontWeight: 600 },
  h4: { fontSize: "1.5rem", lineHeight: 1.3, fontWeight: 600 },
  h5: { fontSize: "1.25rem", lineHeight: 1.4, fontWeight: 600 },
  h6: { fontSize: "1.125rem", lineHeight: 1.4, fontWeight: 600 },
  subtitle: { fontSize: "1.125rem", lineHeight: 1.5, fontWeight: 500 },
  body: { fontSize: "1rem", lineHeight: 1.6, fontWeight: 400 },
  caption: { fontSize: "0.8125rem", lineHeight: 1.5, fontWeight: 400 },
} as const satisfies Record<string, TypeScaleEntry>;

export type TypeScaleKey = keyof typeof typeScale;
