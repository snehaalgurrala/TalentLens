/**
 * Motion tokens consumed by src/design-system/motion/* Framer Motion
 * variants. Centralized so every animated component shares the same feel
 * instead of ad hoc durations/easings per component.
 */
export const duration = {
  fast: 0.15,
  base: 0.25,
  slow: 0.4,
} as const;

export const easing = {
  standard: [0.4, 0, 0.2, 1],
  decelerate: [0, 0, 0.2, 1],
  accelerate: [0.4, 0, 1, 1],
} as const;

export type DurationKey = keyof typeof duration;
export type EasingKey = keyof typeof easing;
