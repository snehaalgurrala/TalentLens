/**
 * z-index scale. Mirrors the `--z-*` theme tokens in globals.css, usable in
 * Tailwind via arbitrary value syntax (`z-(--z-modal)`) or read here for
 * inline styles / Framer Motion `style` props.
 */
export const zIndex = {
  dropdown: 1000,
  sticky: 1100,
  drawer: 1200,
  modal: 1300,
  popover: 1400,
  tooltip: 1500,
  toast: 1600,
} as const;

export type ZIndexKey = keyof typeof zIndex;
