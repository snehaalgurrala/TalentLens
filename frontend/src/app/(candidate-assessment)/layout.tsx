import { AssessmentRunnerProvider } from "@/features/candidate-runner"

export default function CandidateAssessmentLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return <AssessmentRunnerProvider>{children}</AssessmentRunnerProvider>
}
