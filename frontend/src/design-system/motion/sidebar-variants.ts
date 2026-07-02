import type { Variants } from "framer-motion"

import { duration, easing } from "@/design-system/tokens/motion"

export const SIDEBAR_EXPANDED_WIDTH = 272
export const SIDEBAR_COLLAPSED_WIDTH = 72

/** Sidebar shell width collapse/expand. */
export const sidebarWidthVariants: Variants = {
  expanded: {
    width: SIDEBAR_EXPANDED_WIDTH,
    transition: { duration: duration.base, ease: easing.standard },
  },
  collapsed: {
    width: SIDEBAR_COLLAPSED_WIDTH,
    transition: { duration: duration.base, ease: easing.standard },
  },
}

/** Sidebar label text — fades out before the collapse finishes so it doesn't wrap/clip. */
export const sidebarLabelVariants: Variants = {
  expanded: {
    opacity: 1,
    display: "inline",
    transition: { duration: duration.fast, ease: easing.standard },
  },
  collapsed: {
    opacity: 0,
    transitionEnd: { display: "none" },
    transition: { duration: duration.fast, ease: easing.standard },
  },
}
