import { fireEvent, render, screen } from "@testing-library/react"

import { SendAssessmentDialog } from "./send-assessment-dialog"

const mutateMock = jest.fn()

jest.mock("@/hooks/use-assessment-invitations", () => ({
  useSendAssessmentInvitations: () => ({ mutate: mutateMock, isPending: false }),
}))

const CANDIDATES = [
  { candidateId: "cand1", name: "Jane Doe" },
  { candidateId: "cand2", name: "John Smith" },
]

function renderDialog(onOpenChange = jest.fn(), onDone = jest.fn()) {
  return {
    onOpenChange,
    onDone,
    ...render(
      <SendAssessmentDialog
        open
        onOpenChange={onOpenChange}
        campaignId="camp1"
        candidates={CANDIDATES}
        onDone={onDone}
      />
    ),
  }
}

describe("SendAssessmentDialog", () => {
  beforeEach(() => {
    mutateMock.mockReset()
  })

  it("defaults to a 48 hour expiration and sends both candidate ids", () => {
    renderDialog()

    fireEvent.click(screen.getByRole("button", { name: "Send Assessment" }))

    expect(mutateMock).toHaveBeenCalledWith(
      { campaign_id: "camp1", candidate_ids: ["cand1", "cand2"], expiration_hours: 48 },
      expect.anything()
    )
  })

  it("sends the selected preset expiration", () => {
    renderDialog()

    fireEvent.click(screen.getByLabelText("24 hours"))
    fireEvent.click(screen.getByRole("button", { name: "Send Assessment" }))

    expect(mutateMock).toHaveBeenCalledWith(
      expect.objectContaining({ expiration_hours: 24 }),
      expect.anything()
    )
  })

  it("sends a custom expiration when Custom is selected", () => {
    renderDialog()

    fireEvent.click(screen.getByLabelText("Custom"))
    fireEvent.change(screen.getByLabelText("Expiration (hours)"), { target: { value: "120" } })
    fireEvent.click(screen.getByRole("button", { name: "Send Assessment" }))

    expect(mutateMock).toHaveBeenCalledWith(
      expect.objectContaining({ expiration_hours: 120 }),
      expect.anything()
    )
  })

  it("disables Send while the custom expiration is invalid", () => {
    renderDialog()

    fireEvent.click(screen.getByLabelText("Custom"))
    fireEvent.change(screen.getByLabelText("Expiration (hours)"), { target: { value: "0" } })

    expect(screen.getByRole("button", { name: "Send Assessment" })).toBeDisabled()
  })

  it("shows a success/failure breakdown and calls onDone when dismissed", () => {
    mutateMock.mockImplementation((_vars, { onSuccess }) =>
      onSuccess({
        succeeded: [{ candidate_id: "cand1", invitation_id: "inv1" }],
        failed: [{ candidate_id: "cand2", reason: "Candidate has no email on file." }],
      })
    )
    const { onDone, onOpenChange } = renderDialog()

    fireEvent.click(screen.getByRole("button", { name: "Send Assessment" }))

    expect(screen.getByText("Assessment Invitations Sent")).toBeInTheDocument()
    expect(screen.getByText("1 succeeded, 1 failed.")).toBeInTheDocument()
    expect(screen.getByText("John Smith")).toBeInTheDocument()
    expect(screen.getByText("Candidate has no email on file.")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Done" }))
    expect(onDone).toHaveBeenCalled()
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})
