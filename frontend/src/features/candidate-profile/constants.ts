import {
  Archive,
  CheckCircle2,
  CheckSquare,
  Eye,
  FileCheck2,
  ListPlus,
  MessageSquarePlus,
  RotateCcw,
  Sparkles,
  Trophy,
  UploadCloud,
  UserCog,
  UserPlus,
  Workflow,
  XCircle,
  type LucideIcon,
} from "lucide-react"

import type { ActivityEventType } from "@/types"

export const ACTIVITY_LABELS: Record<ActivityEventType, string> = {
  RESUME_UPLOADED: "Resume uploaded",
  PARSING_STARTED: "Parsing started",
  PARSED: "Resume parsed",
  PARSE_FAILED: "Parsing failed",
  RANKED: "Ranked against job description",
  VIEWED: "Profile viewed",
  SHORTLISTED: "Shortlisted",
  REJECTED: "Rejected",
  PIPELINE_STAGE_CHANGED: "Pipeline stage changed",
  RECRUITER_ASSIGNED: "Recruiter assigned",
  NOTE_ADDED: "Note added",
  ARCHIVED: "Archived",
  RESTORED: "Restored",
  TASK_CREATED: "Task created",
  TASK_COMPLETED: "Task completed",
  TASK_REASSIGNED: "Task reassigned",
}

export const ACTIVITY_ICON: Record<ActivityEventType, LucideIcon> = {
  RESUME_UPLOADED: UploadCloud,
  PARSING_STARTED: FileCheck2,
  PARSED: FileCheck2,
  PARSE_FAILED: XCircle,
  RANKED: Sparkles,
  VIEWED: Eye,
  SHORTLISTED: CheckCircle2,
  REJECTED: XCircle,
  PIPELINE_STAGE_CHANGED: Workflow,
  RECRUITER_ASSIGNED: UserPlus,
  NOTE_ADDED: MessageSquarePlus,
  ARCHIVED: Archive,
  RESTORED: RotateCcw,
  TASK_CREATED: ListPlus,
  TASK_COMPLETED: CheckSquare,
  TASK_REASSIGNED: UserCog,
}

export const ACTIVITY_ICON_STYLE: Record<ActivityEventType, string> = {
  RESUME_UPLOADED: "bg-secondary text-secondary-foreground",
  PARSING_STARTED: "bg-secondary text-secondary-foreground",
  PARSED: "bg-primary/10 text-primary",
  PARSE_FAILED: "bg-destructive/10 text-destructive-emphasis",
  RANKED: "bg-accent-purple/10 text-accent-purple-emphasis",
  VIEWED: "bg-muted text-muted-foreground",
  SHORTLISTED: "bg-success/10 text-success-emphasis",
  REJECTED: "bg-destructive/10 text-destructive-emphasis",
  PIPELINE_STAGE_CHANGED: "bg-warning/10 text-warning-emphasis",
  RECRUITER_ASSIGNED: "bg-primary/10 text-primary",
  NOTE_ADDED: "bg-secondary text-secondary-foreground",
  ARCHIVED: "bg-muted text-muted-foreground",
  RESTORED: "bg-primary/10 text-primary",
  TASK_CREATED: "bg-secondary text-secondary-foreground",
  TASK_COMPLETED: "bg-success/10 text-success-emphasis",
  TASK_REASSIGNED: "bg-primary/10 text-primary",
}

// Trophy icon reserved for the HIRED pipeline-stage-changed special case, applied at render time.
export const HIRED_ICON: LucideIcon = Trophy

// Client-side skill categorization — the resume parser doesn't tag categories,
// so this buckets by keyword match against common skill names. Anything that
// doesn't match a bucket falls into "Other".
export const SKILL_CATEGORIES: { label: string; keywords: string[] }[] = [
  {
    label: "Programming",
    keywords: ["python", "java", "c++", "c#", "go", "golang", "rust", "ruby", "php", "kotlin", "swift", "scala", "typescript", "javascript"],
  },
  {
    label: "Frontend",
    keywords: ["react", "vue", "angular", "next.js", "nextjs", "html", "css", "tailwind", "redux", "svelte"],
  },
  {
    label: "Backend",
    keywords: ["node", "express", "django", "flask", "fastapi", "spring", "rails", "asp.net", ".net", "graphql", "rest api"],
  },
  {
    label: "Cloud",
    keywords: ["aws", "azure", "gcp", "google cloud", "amazon web services", "lambda", "s3", "ec2"],
  },
  {
    label: "DevOps",
    keywords: ["docker", "kubernetes", "k8s", "ci/cd", "jenkins", "terraform", "ansible", "github actions"],
  },
  {
    label: "Database",
    keywords: ["sql", "postgres", "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "dynamodb", "oracle"],
  },
  {
    label: "AI/ML",
    keywords: ["machine learning", "ml", "ai", "artificial intelligence", "nlp", "tensorflow", "pytorch", "deep learning", "llm"],
  },
  {
    label: "Soft Skills",
    keywords: ["communication", "leadership", "teamwork", "collaboration", "problem solving", "mentoring", "agile", "scrum"],
  },
]

export function categorizeSkill(skill: string): string {
  const normalized = skill.toLowerCase().trim()
  for (const category of SKILL_CATEGORIES) {
    if (category.keywords.some((keyword) => normalized.includes(keyword))) {
      return category.label
    }
  }
  return "Other"
}
