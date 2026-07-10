import type { PipelineStage } from "@/types"

export interface PipelineBoardColumn {
  key: string
  label: string
  /** All raw PipelineStage values grouped into this column (usually one). */
  stages: PipelineStage[]
}

/** Column order for the active (non-terminal) part of the board. Terminal
 * stages (REJECTED/WITHDRAWN/ARCHIVED) render in a separate collapsed
 * section instead of taking up space in the main horizontal scroll.
 *
 * Purely a rendering of backend-driven candidate.pipeline_stage — there is
 * no drag-and-drop or other client-side stage mutation on this board. The
 * only way a card changes columns is a real backend transition (automatic,
 * or via an explicit action like Shortlist/Send Assessment elsewhere in the
 * app), reflected here on next refetch. */
export const PIPELINE_BOARD_COLUMNS: PipelineBoardColumn[] = [
  { key: "APPLIED", label: "Applied", stages: ["APPLIED"] },
  { key: "AI_PROCESSING", label: "AI Processing", stages: ["PARSING", "EMBEDDING"] },
  { key: "RANKED", label: "Ranked", stages: ["RANKED"] },
  { key: "SHORTLISTED", label: "Shortlisted", stages: ["SHORTLISTED"] },
  { key: "ASSESSMENT_SENT", label: "Assessment Sent", stages: ["ASSESSMENT_SENT"] },
  {
    key: "ASSESSMENT_IN_PROGRESS",
    label: "Assessment In Progress",
    stages: ["ASSESSMENT_IN_PROGRESS"],
  },
  {
    key: "ASSESSMENT_COMPLETED",
    label: "Assessment Completed",
    stages: ["ASSESSMENT_COMPLETED"],
  },
  {
    key: "INTERVIEW_SCHEDULED",
    label: "Interview Scheduled",
    stages: ["INTERVIEW_SCHEDULED"],
  },
  {
    key: "INTERVIEW_COMPLETED",
    label: "Interview Completed",
    stages: ["INTERVIEW_COMPLETED"],
  },
  { key: "OFFER_EXTENDED", label: "Offer Extended", stages: ["OFFER_EXTENDED"] },
  { key: "OFFER_ACCEPTED", label: "Offer Accepted", stages: ["OFFER_ACCEPTED"] },
  { key: "HIRED", label: "Hired", stages: ["HIRED"] },
]

export const TERMINAL_BOARD_COLUMNS: PipelineBoardColumn[] = [
  { key: "REJECTED", label: "Rejected", stages: ["REJECTED"] },
  { key: "WITHDRAWN", label: "Withdrawn", stages: ["WITHDRAWN"] },
  { key: "ARCHIVED", label: "Archived", stages: ["ARCHIVED"] },
]

export function columnForStage(stage: PipelineStage): PipelineBoardColumn | undefined {
  return [...PIPELINE_BOARD_COLUMNS, ...TERMINAL_BOARD_COLUMNS].find((c) => c.stages.includes(stage))
}
