import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"

import { jobDescriptionService } from "@/services/job-description.service"
import type { JobDescription } from "@/types"

import { JdPanel } from "./jd-panel"

jest.mock("@/services/job-description.service", () => ({
  jobDescriptionService: {
    listByCampaign: jest.fn(),
    createFromText: jest.fn(),
    uploadFile: jest.fn(),
    remove: jest.fn(),
    download: jest.fn(),
  },
}))

const mockedJdService = jest.mocked(jobDescriptionService)

const JD: JobDescription = {
  id: "jd1",
  campaign_id: "c1",
  created_by: "u1",
  original_filename: "job-description.pdf",
  storage_path: "job-descriptions/c1/jd1.pdf",
  mime_type: "application/pdf",
  file_size: 2048,
  raw_text: "We are hiring a Senior Backend Engineer with 5+ years of experience.",
  structured_json: { required_skills: ["Python", "SQL"] },
  parser_version: "v1",
  parsed_at: "2026-06-01T00:00:00Z",
  parsing_status: "COMPLETED",
  parsing_error: null,
  embedding_status: "READY",
  embedding_model: "bge-large",
  embedding_generated_at: "2026-06-01T00:00:00Z",
  embedding_dimension: 1024,
  is_deleted: false,
  created_at: "2026-06-01T00:00:00Z",
  updated_at: "2026-06-01T00:00:00Z",
}

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe("JdPanel", () => {
  afterEach(() => {
    jest.clearAllMocks()
  })

  it("shows an empty state and add action when no job description exists", async () => {
    mockedJdService.listByCampaign.mockResolvedValue([])
    renderWithClient(<JdPanel campaignId="c1" />)

    await waitFor(() => expect(screen.getByText("No job description yet")).toBeInTheDocument())
    expect(screen.getByRole("button", { name: /add job description/i })).toBeInTheDocument()
  })

  it("renders the current job description's text and pipeline status", async () => {
    mockedJdService.listByCampaign.mockResolvedValue([JD])
    renderWithClient(<JdPanel campaignId="c1" />)

    await waitFor(() => expect(screen.getByText("job-description.pdf")).toBeInTheDocument())
    expect(screen.getByText(/We are hiring a Senior Backend Engineer/)).toBeInTheDocument()
    expect(screen.getByText("Parsing: COMPLETED")).toBeInTheDocument()
    expect(screen.getByText("Embedding: READY")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /download/i })).toBeInTheDocument()
  })
})
