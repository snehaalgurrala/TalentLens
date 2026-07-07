import type { AptitudeQuestion, AssessmentMeta } from "./types"

export const assessmentMeta: AssessmentMeta = {
  title: "Frontend Engineer — Communication & Aptitude Assessment",
  companyName: "TalentLens",
  estimatedMinutes: 12,
}

export const aptitudeQuestions: AptitudeQuestion[] = [
  {
    id: 1,
    prompt: "A train travels 60 miles in 45 minutes. What is its average speed in miles per hour?",
    options: [
      { id: "a", label: "70 mph" },
      { id: "b", label: "75 mph" },
      { id: "c", label: "80 mph" },
      { id: "d", label: "90 mph" },
    ],
  },
  {
    id: 2,
    prompt: "What number comes next in the sequence? 2, 6, 12, 20, 30, ?",
    options: [
      { id: "a", label: "36" },
      { id: "b", label: "40" },
      { id: "c", label: "42" },
      { id: "d", label: "48" },
    ],
  },
  {
    id: 3,
    prompt: "Book is to Reading as Fork is to ___",
    options: [
      { id: "a", label: "Kitchen" },
      { id: "b", label: "Eating" },
      { id: "c", label: "Utensil" },
      { id: "d", label: "Cooking" },
    ],
  },
  {
    id: 4,
    prompt:
      "All engineers are problem solvers. Some problem solvers are managers. Which conclusion is valid?",
    options: [
      { id: "a", label: "All engineers are managers" },
      { id: "b", label: "Some engineers are managers" },
      { id: "c", label: "Some managers may be engineers" },
      { id: "d", label: "No engineers are managers" },
    ],
  },
  {
    id: 5,
    prompt: "A shirt originally priced $80 is discounted by 25%. What is the sale price?",
    options: [
      { id: "a", label: "$55" },
      { id: "b", label: "$58" },
      { id: "c", label: "$60" },
      { id: "d", label: "$65" },
    ],
  },
]

export const readAloudSentence =
  "The quick brown fox jumps over the lazy dog while carrying a bag of documents to the office."

export const listenRepeatSentence =
  "Innovation distinguishes between a leader and a follower in every industry we serve."

export const SECTION1_DURATION_SECONDS = 10 * 60
