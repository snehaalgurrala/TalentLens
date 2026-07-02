"use client"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { DataTable, type DataTableColumn } from "@/components/ui/data-table"
import { formatDate, initialsFromName } from "@/utils"
import type { CandidateListItem } from "@/types"

import { CandidateActionsMenu } from "./candidate-actions-menu"
import { PipelineStageBadge, RecommendationBadge } from "./candidate-badges"
import { CandidateScoreCell } from "./candidate-score-cell"
import { REVIEW_STATUS_VARIANT } from "./constants"

export interface CandidatesTableProps {
  candidates: CandidateListItem[]
  isLoading: boolean
  rankingAvailable: boolean
  selectedIds: Set<string>
  onToggleSelect: (id: string) => void
  onToggleSelectAll: () => void
  onEditNotes: (candidate: CandidateListItem) => void
  onRowClick?: (candidate: CandidateListItem) => void
  sortKey?: string
  sortDirection?: "asc" | "desc"
  onSortChange: (key: string) => void
}

function SkillsCell({ skills }: { skills: string[] }) {
  if (skills.length === 0) {
    return <span className="text-muted-foreground">—</span>
  }
  const visible = skills.slice(0, 3)
  const remaining = skills.length - visible.length
  return (
    <div className="flex max-w-56 flex-wrap gap-1">
      {visible.map((skill) => (
        <Badge key={skill} variant="outline">
          {skill}
        </Badge>
      ))}
      {remaining > 0 && <Badge variant="secondary">+{remaining}</Badge>}
    </div>
  )
}

function EducationCell({ education }: { education: CandidateListItem["education"] }) {
  const top = education[0]
  if (!top) {
    return <span className="text-muted-foreground">—</span>
  }
  return (
    <div className="flex flex-col">
      <span className="text-foreground">{top.degree || top.field || "—"}</span>
      {top.institution && <span className="text-caption text-muted-foreground">{top.institution}</span>}
    </div>
  )
}

function CandidatesTable({
  candidates,
  isLoading,
  rankingAvailable,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onEditNotes,
  onRowClick,
  sortKey,
  sortDirection,
  onSortChange,
}: CandidatesTableProps) {
  const allSelected = candidates.length > 0 && candidates.every((c) => selectedIds.has(c.resume_file_id))

  const columns: DataTableColumn<CandidateListItem>[] = [
    {
      key: "select",
      header: (
        <Checkbox
          checked={allSelected}
          onCheckedChange={onToggleSelectAll}
          aria-label="Select all candidates"
          onClick={(event) => event.stopPropagation()}
        />
      ),
      render: (candidate) => (
        <Checkbox
          checked={selectedIds.has(candidate.resume_file_id)}
          onCheckedChange={() => onToggleSelect(candidate.resume_file_id)}
          onClick={(event) => event.stopPropagation()}
          aria-label={`Select ${candidate.candidate_name}`}
        />
      ),
    },
    {
      key: "rank",
      header: "Rank",
      align: "center",
      render: (candidate) => candidate.rank ?? <span className="text-muted-foreground">—</span>,
    },
    {
      key: "candidate_name",
      header: "Candidate",
      sortable: true,
      render: (candidate) => (
        <div className="flex items-center gap-2.5">
          <Avatar size="sm">
            <AvatarFallback>{initialsFromName(candidate.candidate_name)}</AvatarFallback>
          </Avatar>
          <div className="flex flex-col">
            <span className="font-medium text-foreground">{candidate.candidate_name}</span>
            {candidate.email && <span className="text-caption text-muted-foreground">{candidate.email}</span>}
          </div>
        </div>
      ),
    },
    {
      key: "current_company",
      header: "Current Company",
      render: (candidate) => candidate.current_company || <span className="text-muted-foreground">—</span>,
    },
    {
      key: "current_role",
      header: "Current Role",
      render: (candidate) => candidate.current_role || <span className="text-muted-foreground">—</span>,
    },
    {
      key: "years_of_experience",
      header: "Experience",
      sortable: true,
      render: (candidate) =>
        candidate.years_of_experience !== null ? (
          `${candidate.years_of_experience} yrs`
        ) : (
          <span className="text-muted-foreground">—</span>
        ),
    },
    {
      key: "education",
      header: "Education",
      render: (candidate) => <EducationCell education={candidate.education} />,
    },
    {
      key: "skills",
      header: "Skills",
      render: (candidate) => <SkillsCell skills={candidate.skills} />,
    },
    {
      key: "overall_score",
      header: "Match Score",
      sortable: true,
      render: (candidate) =>
        rankingAvailable ? (
          <CandidateScoreCell score={candidate.overall_score} />
        ) : (
          <span className="text-muted-foreground">—</span>
        ),
    },
    {
      key: "recommendation",
      header: "AI Recommendation",
      render: (candidate) => <RecommendationBadge recommendation={candidate.recommendation} />,
    },
    {
      key: "review_status",
      header: "Resume Status",
      render: (candidate) => (
        <Badge variant={REVIEW_STATUS_VARIANT[candidate.review_status]}>{candidate.review_status}</Badge>
      ),
    },
    {
      key: "pipeline_stage",
      header: "Pipeline Stage",
      render: (candidate) => <PipelineStageBadge stage={candidate.pipeline_stage} />,
    },
    {
      key: "recruiter",
      header: "Recruiter",
      render: (candidate) =>
        candidate.assigned_recruiter ? (
          <div className="flex items-center gap-2">
            <Avatar size="sm">
              <AvatarFallback>{initialsFromName(candidate.assigned_recruiter.full_name)}</AvatarFallback>
            </Avatar>
            <span>{candidate.assigned_recruiter.full_name}</span>
          </div>
        ) : (
          <span className="text-muted-foreground">Unassigned</span>
        ),
    },
    {
      key: "applied_at",
      header: "Uploaded Date",
      sortable: true,
      render: (candidate) => formatDate(candidate.applied_at),
    },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (candidate) => (
        <div onClick={(event) => event.stopPropagation()}>
          <CandidateActionsMenu candidate={candidate} onEditNotes={onEditNotes} />
        </div>
      ),
    },
  ]

  return (
    <DataTable
      columns={columns}
      data={candidates}
      getRowKey={(candidate) => candidate.resume_file_id}
      state={isLoading ? "loading" : candidates.length === 0 ? "empty" : "ready"}
      emptyTitle="No candidates yet"
      emptyDescription="Upload resumes to this campaign to start reviewing candidates."
      sortKey={sortKey}
      sortDirection={sortDirection}
      onSortChange={onSortChange}
      onRowClick={onRowClick}
      className="[&_table]:min-w-max"
    />
  )
}

export { CandidatesTable }
