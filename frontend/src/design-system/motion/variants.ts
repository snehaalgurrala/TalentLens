import type { Variants } from "framer-motion"

import { duration, easing } from "@/design-system/tokens/motion"

/** Generic opacity fade. Use for content that just needs to appear/disappear. */
export const fadeVariants: Variants = {
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

/** Fade + rise. Use for cards, list items, page sections entering view. */
export const slideUpVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: duration.base, ease: easing.decelerate },
  },
  exit: {
    opacity: 0,
    y: 8,
    transition: { duration: duration.fast, ease: easing.accelerate },
  },
}

/** Fade + horizontal slide. Use for tab panels, stepper content. */
export const slideRightVariants: Variants = {
  hidden: { opacity: 0, x: -8 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: duration.base, ease: easing.decelerate },
  },
  exit: {
    opacity: 0,
    x: 8,
    transition: { duration: duration.fast, ease: easing.accelerate },
  },
}

/** Subtle lift for hover-interactive surfaces (cards, buttons as motion.div). */
export const hoverLift = {
  whileHover: { y: -2 },
  whileTap: { y: 0 },
  transition: { duration: duration.fast, ease: easing.standard },
}
