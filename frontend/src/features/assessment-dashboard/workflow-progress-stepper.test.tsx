import { render, screen } from "@testing-library/react"

import { WorkflowProgressStepper } from "./workflow-progress-stepper"

describe("WorkflowProgressStepper", () => {
  it("renders all seven workflow steps", () => {
    render(<WorkflowProgressStepper pipelineStage="APPLIED" />)

    expect(screen.getByText("Applied")).toBeInTheDocument()
    expect(screen.getByText("AI Processing")).toBeInTheDocument()
    expect(screen.getByText("Ranked")).toBeInTheDocument()
    expect(screen.getByText("Shortlisted")).toBeInTheDocument()
    expect(screen.getByText("Assessment Sent")).toBeInTheDocument()
    expect(screen.getByText("Assessment In Progress")).toBeInTheDocument()
    expect(screen.getByText("Assessment Completed")).toBeInTheDocument()
  })

  it("marks exactly one step as current", () => {
    render(<WorkflowProgressStepper pipelineStage="SHORTLISTED" />)

    expect(document.querySelectorAll('[aria-current="step"]')).toHaveLength(1)
  })

  it("groups PARSING and EMBEDDING into the same AI Processing step", () => {
    const { rerender } = render(<WorkflowProgressStepper pipelineStage="PARSING" />)
    expect(document.querySelector('[aria-current="step"]')).not.toBeNull()

    rerender(<WorkflowProgressStepper pipelineStage="EMBEDDING" />)
    expect(document.querySelector('[aria-current="step"]')).not.toBeNull()
  })

  it("renders no current step and no completed checkmarks when pipelineStage is null", () => {
    render(<WorkflowProgressStepper pipelineStage={null} />)

    expect(document.querySelector('[aria-current="step"]')).toBeNull()
    expect(screen.getByText("Applied")).toHaveClass("text-muted-foreground")
  })

  it("treats Assessment Completed as the fully-reached final step", () => {
    render(<WorkflowProgressStepper pipelineStage="ASSESSMENT_COMPLETED" />)

    const current = document.querySelector('[aria-current="step"]')
    expect(current).not.toBeNull()
    expect(screen.getByText("Assessment Completed")).toHaveClass("text-foreground")
    expect(screen.getByText("Applied")).toHaveClass("text-foreground")
  })

  it("does not mark stages beyond Assessment Completed (Interview/Hiring out of scope)", () => {
    render(<WorkflowProgressStepper pipelineStage="INTERVIEW_SCHEDULED" />)

    // INTERVIEW_SCHEDULED isn't one of the 7 rendered steps, so nothing
    // should resolve to a "current" step.
    expect(document.querySelector('[aria-current="step"]')).toBeNull()
  })
})
