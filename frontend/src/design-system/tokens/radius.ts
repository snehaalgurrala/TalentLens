/**
 * Border-radius scale. Mirrors the `--radius-*` theme tokens in globals.css
 * (`rounded-sm` ... `rounded-xl` utilities), all derived from the single
 * `--radius` base so a future brand refresh only touches one value.
 */
export const radius = {
  sm: "calc(0.5rem - 4px)",
  md: "calc(0.5rem - 2px)",
  lg: "0.5rem",
  xl: "calc(0.5rem + 4px)",
  full: "9999px",
} as const;

export type RadiusKey = keyof typeof radius;
