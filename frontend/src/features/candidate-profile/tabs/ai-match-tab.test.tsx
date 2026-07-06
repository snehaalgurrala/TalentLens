import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"

import { candidateService } from "@/services/candidate.service"
import type { CandidateMatchAnalysis } from "@/types"

import { AiMatchTab } from "./ai-match-tab"

jest.mock("@/services/candidate.service", () => ({
  candidateService: { getMatchAnalysis: jest.fn() },
}))

const mockedCandidateService = jest.mocked(candidateService)

const ANALYSIS: CandidateMatchAnalysis = {
  overall_score: 88,
  recommendation: "Strong Match",
  sub_scores: {
    semantic_score: 80,
    skills_score: 90,
    experience_score: 85,
    education_score: 100,
    projects_score: 70,
    certification_score: 60,
  },
  bonus_points: 5,
  preferred_company_matched: true,
  scoring_rule_source: "organization_default",
  match_explanation: "Jane Doe scored 88/100 overall (Strong Match).",
  strengths: ["Skills: 9/10 required skills matched."],
  weaknesses: ["Certifications: 0/2 certification(s) matched."],
  semantic_details: { cosine_similarity: 0.8 },
  skills_details: {
    required: {
      skills: ["Python", "SQL"],
      exact_matches: ["Python"],
      synonym_matches: [],
      partial_matches: [],
      missing: ["SQL"],
    },
    preferred: { skills: [], exact_matches: [], synonym_matches: [], partial_matches: [], missing: [] },
  },
  experience_details: { candidate_years: 5, required_min_years: 3 },
  education_details: { requirements: [] },
  projects_details: { requirements: [] },
  certification_details: { required: [], matched: [], missing: [] },
  explanation_items: [
    { text: "Excellent Python experience.", sentiment: "positive", category: "skills" },
    { text: "Missing SQL experience.", sentiment: "negative", category: "skills" },
  ],
}

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe("AiMatchTab", () => {
  afterEach(() => jest.clearAllMocks())

  it("shows a not-yet-ranked message on a 422 response", async () => {
    mockedCandidateService.getMatchAnalysis.mockRejectedValue({
      status: 422,
      message: "This candidate has not been ranked yet.",
    })
    renderWithClient(<AiMatchTab candidateId="cand1" />)

    expect(await screen.findByText("This candidate has not been ranked yet.")).toBeInTheDocument()
  })

  it("renders scores, matched/missing skills, and explanation bullets", async () => {
    mockedCandidateService.getMatchAnalysis.mockResolvedValue(ANALYSIS)
    renderWithClient(<AiMatchTab candidateId="cand1" />)

    expect(await screen.findByText("88%")).toBeInTheDocument()
    expect(screen.getByText("Python")).toBeInTheDocument()
    expect(screen.getByText("SQL")).toBeInTheDocument()
    expect(screen.getByText("Excellent Python experience.")).toBeInTheDocument()
    expect(screen.getByText(/preferred-employer bonus/)).toBeInTheDocument()
  })
})
