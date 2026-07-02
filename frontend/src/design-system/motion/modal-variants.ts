import type { Variants } from "framer-motion"

import { duration, easing } from "@/design-system/tokens/motion"

/** Dialog/modal overlay backdrop. */
export const modalOverlayVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: duration.base, ease: easing.standard },
  },
  exit: {
    opacity: 0,
    transition: { duration: duration.fast, ease: easing.accelerate },
  },
}

/** Dialog/modal content panel — scale + fade, matching Radix's data-state timing. */
export const modalContentVariants: Variants = {
  hidden: { opacity: 0, scale: 0.96, y: 8 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { duration: duration.base, ease: easing.decelerate },
  },
  exit: {
    opacity: 0,
    scale: 0.96,
    y: 8,
    transition: { duration: duration.fast, ease: easing.accelerate },
  },
}
