import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"

import { candidateService } from "@/services/candidate.service"
import type { ResumeFile } from "@/types"

import { ResumeUploadPanel } from "./resume-upload-panel"

jest.mock("@/services/candidate.service", () => ({
  candidateService: {
    listResumes: jest.fn(),
    uploadResumes: jest.fn(),
    deleteResume: jest.fn(),
    listRankings: jest.fn(),
  },
}))

const mockedCandidateService = jest.mocked(candidateService)

const EXISTING_RESUME: ResumeFile = {
  id: "rf1",
  campaign_id: "c1",
  original_filename: "jane-doe.pdf",
  stored_filename: "stored.pdf",
  mime_type: "application/pdf",
  file_size: 1024,
  storage_path: "c1/stored.pdf",
  upload_status: "PARSED",
  uploaded_by: "u1",
  candidate_id: "cand1",
  error_message: null,
  review_status: "PENDING",
  is_deleted: false,
  uploaded_at: "2026-06-01T00:00:00Z",
  pipeline_stage: "APPLIED",
  assigned_recruiter_id: null,
  notes: null,
}

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

function makeFile(name: string): File {
  return new File(["content"], name, { type: "application/pdf" })
}

describe("ResumeUploadPanel", () => {
  afterEach(() => {
    jest.clearAllMocks()
  })

  it("shows an empty state when no resumes have been uploaded", async () => {
    mockedCandidateService.listResumes.mockResolvedValue([])
    renderWithClient(<ResumeUploadPanel campaignId="c1" />)

    await waitFor(() => expect(screen.getByText("No uploads yet")).toBeInTheDocument())
  })

  it("lists uploaded resumes with their processing status", async () => {
    mockedCandidateService.listResumes.mockResolvedValue([EXISTING_RESUME])
    renderWithClient(<ResumeUploadPanel campaignId="c1" />)

    await waitFor(() => expect(screen.getByText("jane-doe.pdf")).toBeInTheDocument())
    expect(screen.getByText("PARSED")).toBeInTheDocument()
  })

  it("warns about a duplicate filename before uploading", async () => {
    mockedCandidateService.listResumes.mockResolvedValue([EXISTING_RESUME])
    renderWithClient(<ResumeUploadPanel campaignId="c1" />)

    await waitFor(() => expect(screen.getByText("jane-doe.pdf")).toBeInTheDocument())

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, { target: { files: [makeFile("jane-doe.pdf")] } })

    await waitFor(() =>
      expect(screen.getByText(/possible duplicates already in this campaign/i)).toBeInTheDocument()
    )
  })

  it("uploads staged files and reports the success count", async () => {
    mockedCandidateService.listResumes.mockResolvedValue([])
    mockedCandidateService.uploadResumes.mockResolvedValue({
      uploaded: [{ ...EXISTING_RESUME, original_filename: "new-resume.pdf" }],
      count: 1,
    })
    renderWithClient(<ResumeUploadPanel campaignId="c1" />)

    await waitFor(() => expect(screen.getByText("No uploads yet")).toBeInTheDocument())

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, { target: { files: [makeFile("new-resume.pdf")] } })

    fireEvent.click(screen.getByRole("button", { name: /upload 1 file/i }))

    await waitFor(() => expect(mockedCandidateService.uploadResumes).toHaveBeenCalled())
    expect(mockedCandidateService.uploadResumes.mock.calls[0][1]).toEqual([expect.any(File)])
  })
})
