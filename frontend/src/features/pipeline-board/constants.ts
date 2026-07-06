import type { PipelineStage } from "@/types"

export interface PipelineBoardColumn {
  key: string
  label: string
  /** All raw PipelineStage values grouped into this column (usually one). */
  stages: PipelineStage[]
  /** The stage a drag-drop or manual move into this column actually sets —
   * the first stage in `stages` for single-stage columns. */
  targetStage: PipelineStage
}

/** Column order for the active (non-terminal) part of the board. Terminal
 * stages (REJECTED/WITHDRAWN/ARCHIVED) render in a separate collapsed
 * section instead of taking up space in the main horizontal scroll. */
export const PIPELINE_BOARD_COLUMNS: PipelineBoardColumn[] = [
  { key: "APPLIED", label: "Applied", stages: ["APPLIED"], targetStage: "APPLIED" },
  {
    key: "AI_PROCESSING",
    label: "AI Processing",
    stages: ["PARSING", "EMBEDDING"],
    targetStage: "PARSING",
  },
  { key: "RANKED", label: "Ranked", stages: ["RANKED"], targetStage: "RANKED" },
  { key: "SHORTLISTED", label: "Shortlisted", stages: ["SHORTLISTED"], targetStage: "SHORTLISTED" },
  {
    key: "ASSESSMENT_SENT",
    label: "Assessment Sent",
    stages: ["ASSESSMENT_SENT"],
    targetStage: "ASSESSMENT_SENT",
  },
  {
    key: "ASSESSMENT_COMPLETED",
    label: "Assessment Completed",
    stages: ["ASSESSMENT_COMPLETED"],
    targetStage: "ASSESSMENT_COMPLETED",
  },
  {
    key: "INTERVIEW_SCHEDULED",
    label: "Interview Scheduled",
    stages: ["INTERVIEW_SCHEDULED"],
    targetStage: "INTERVIEW_SCHEDULED",
  },
  {
    key: "INTERVIEW_COMPLETED",
    label: "Interview Completed",
    stages: ["INTERVIEW_COMPLETED"],
    targetStage: "INTERVIEW_COMPLETED",
  },
  {
    key: "OFFER_EXTENDED",
    label: "Offer Extended",
    stages: ["OFFER_EXTENDED"],
    targetStage: "OFFER_EXTENDED",
  },
  {
    key: "OFFER_ACCEPTED",
    label: "Offer Accepted",
    stages: ["OFFER_ACCEPTED"],
    targetStage: "OFFER_ACCEPTED",
  },
  { key: "HIRED", label: "Hired", stages: ["HIRED"], targetStage: "HIRED" },
]

export const TERMINAL_BOARD_COLUMNS: PipelineBoardColumn[] = [
  { key: "REJECTED", label: "Rejected", stages: ["REJECTED"], targetStage: "REJECTED" },
  { key: "WITHDRAWN", label: "Withdrawn", stages: ["WITHDRAWN"], targetStage: "WITHDRAWN" },
  { key: "ARCHIVED", label: "Archived", stages: ["ARCHIVED"], targetStage: "ARCHIVED" },
]

export function columnForStage(stage: PipelineStage): PipelineBoardColumn | undefined {
  return [...PIPELINE_BOARD_COLUMNS, ...TERMINAL_BOARD_COLUMNS].find((c) => c.stages.includes(stage))
}
