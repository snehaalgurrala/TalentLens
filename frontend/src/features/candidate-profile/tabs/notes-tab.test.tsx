import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"

import { candidateService } from "@/services/candidate.service"
import type { CandidateNote } from "@/types"

import { NotesTab } from "./notes-tab"

jest.mock("@/services/candidate.service", () => ({
  candidateService: {
    listNotes: jest.fn(),
    createNote: jest.fn(),
    updateNote: jest.fn(),
    deleteNote: jest.fn(),
    pinNote: jest.fn(),
  },
}))
jest.mock("@/services/organization.service", () => ({
  organizationService: { listMembers: jest.fn().mockResolvedValue([]) },
}))

const mockedCandidateService = jest.mocked(candidateService)

const OWN_NOTE: CandidateNote = {
  id: "n1",
  resume_file_id: "rf1",
  author: { id: "u1", full_name: "Current User", email: "me@example.com", role: "RECRUITER" },
  body: "Strong candidate.",
  created_at: "2026-06-01T00:00:00Z",
  updated_at: "2026-06-01T00:00:00Z",
  can_edit: true,
  is_pinned: false,
  mentioned_user_ids: [],
}

const OTHER_NOTE: CandidateNote = {
  id: "n2",
  resume_file_id: "rf1",
  author: { id: "u2", full_name: "Other Recruiter", email: "other@example.com", role: "RECRUITER" },
  body: "Needs a follow-up interview.",
  created_at: "2026-06-01T00:00:00Z",
  updated_at: "2026-06-01T00:00:00Z",
  can_edit: false,
  is_pinned: false,
  mentioned_user_ids: [],
}

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe("NotesTab", () => {
  afterEach(() => jest.clearAllMocks())

  it("renders notes and only shows edit/delete for the caller's own note", async () => {
    mockedCandidateService.listNotes.mockResolvedValue([OWN_NOTE, OTHER_NOTE])
    renderWithClient(<NotesTab candidateId="cand1" />)

    expect(await screen.findByText("Strong candidate.")).toBeInTheDocument()
    expect(await screen.findByText("Needs a follow-up interview.")).toBeInTheDocument()
    expect(await screen.findAllByRole("button", { name: "Edit note" })).toHaveLength(1)
    expect(await screen.findAllByRole("button", { name: "Delete note" })).toHaveLength(1)
  })

  it("shows an empty state when there are no notes", async () => {
    mockedCandidateService.listNotes.mockResolvedValue([])
    renderWithClient(<NotesTab candidateId="cand1" />)

    expect(await screen.findByText("No notes yet")).toBeInTheDocument()
  })

  it("creates a note from the composer", async () => {
    mockedCandidateService.listNotes.mockResolvedValue([])
    mockedCandidateService.createNote.mockResolvedValue(OWN_NOTE)
    renderWithClient(<NotesTab candidateId="cand1" />)

    await screen.findByText("No notes yet")
    fireEvent.change(screen.getByPlaceholderText(/add a note/i), {
      target: { value: "Strong candidate." },
    })
    fireEvent.click(screen.getByRole("button", { name: "Add Note" }))

    await waitFor(() =>
      expect(mockedCandidateService.createNote).toHaveBeenCalledWith("cand1", "Strong candidate.", [])
    )
  })

  it("deletes the caller's own note", async () => {
    mockedCandidateService.listNotes.mockResolvedValue([OWN_NOTE])
    mockedCandidateService.deleteNote.mockResolvedValue(undefined)
    renderWithClient(<NotesTab candidateId="cand1" />)

    await screen.findByText("Strong candidate.")
    fireEvent.click(screen.getByRole("button", { name: "Delete note" }))

    await waitFor(() => expect(mockedCandidateService.deleteNote).toHaveBeenCalledWith("cand1", "n1"))
  })
})
