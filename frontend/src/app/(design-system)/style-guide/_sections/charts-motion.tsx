"use client"

import * as React from "react"
import { AnimatePresence, motion } from "framer-motion"
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { useChartTheme } from "@/design-system/charts/useChartTheme"
import { fadeVariants, hoverLift, slideUpVariants } from "@/design-system/motion/variants"
import { Button } from "@/components/ui/button"
import { Row, Section } from "../_components/section"

const data = [
  { stage: "Applied", candidates: 240 },
  { stage: "Screened", candidates: 140 },
  { stage: "Interviewed", candidates: 62 },
  { stage: "Offered", candidates: 18 },
]

function ChartsMotionSection() {
  const { palette, defaults } = useChartTheme()
  const [visible, setVisible] = React.useState(true)

  return (
    <Section
      id="charts-motion"
      title="Charts & motion"
      description="Recharts themed with only TalentSmart brand colors, and Framer Motion variants centralized in design-system/motion."
    >
      <Row label="Chart">
        <div className="h-64 w-full max-w-lg">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <CartesianGrid
                stroke={defaults.grid.stroke}
                strokeDasharray={defaults.grid.strokeDasharray}
                vertical={false}
              />
              <XAxis
                dataKey="stage"
                stroke={defaults.axis.stroke}
                fontSize={defaults.axis.fontSize}
                tickLine={false}
              />
              <YAxis
                stroke={defaults.axis.stroke}
                fontSize={defaults.axis.fontSize}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                contentStyle={defaults.tooltip.contentStyle}
                labelStyle={defaults.tooltip.labelStyle}
              />
              <Bar
                dataKey="candidates"
                fill={palette[0]}
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Row>

      <Row label="Fade / slide">
        <div className="flex flex-col gap-3">
          <Button
            size="sm"
            variant="outline"
            className="w-fit"
            onClick={() => setVisible((v) => !v)}
          >
            Toggle
          </Button>
          <div className="h-16">
            <AnimatePresence mode="wait">
              {visible && (
                <motion.div
                  key="fade"
                  variants={fadeVariants}
                  initial="hidden"
                  animate="visible"
                  exit="exit"
                  className="flex items-center gap-3"
                >
                  <motion.span
                    variants={slideUpVariants}
                    className="rounded-md border border-border bg-surface px-3 py-2 text-sm"
                  >
                    fadeVariants
                  </motion.span>
                  <motion.span
                    variants={slideUpVariants}
                    className="rounded-md border border-border bg-surface px-3 py-2 text-sm"
                  >
                    slideUpVariants
                  </motion.span>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </Row>

      <Row label="Hover lift">
        <motion.div
          {...hoverLift}
          className="cursor-pointer rounded-lg border border-border bg-surface px-4 py-3 text-sm shadow-elevation-1"
        >
          Hover me
        </motion.div>
      </Row>
    </Section>
  )
}

export { ChartsMotionSection }
