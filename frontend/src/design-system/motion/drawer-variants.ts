import type { Variants } from "framer-motion"

import { duration, easing } from "@/design-system/tokens/motion"

/** Drawer/sheet sliding in from the right edge. */
export const drawerRightVariants: Variants = {
  hidden: { x: "100%" },
  visible: {
    x: 0,
    transition: { duration: duration.slow, ease: easing.decelerate },
  },
  exit: {
    x: "100%",
    transition: { duration: duration.base, ease: easing.accelerate },
  },
}

/** Drawer/sheet sliding in from the left edge. */
export const drawerLeftVariants: Variants = {
  hidden: { x: "-100%" },
  visible: {
    x: 0,
    transition: { duration: duration.slow, ease: easing.decelerate },
  },
  exit: {
    x: "-100%",
    transition: { duration: duration.base, ease: easing.accelerate },
  },
}

/** Drawer/sheet sliding up from the bottom edge (mobile action sheets). */
export const drawerBottomVariants: Variants = {
  hidden: { y: "100%" },
  visible: {
    y: 0,
    transition: { duration: duration.slow, ease: easing.decelerate },
  },
  exit: {
    y: "100%",
    transition: { duration: duration.base, ease: easing.accelerate },
  },
}
