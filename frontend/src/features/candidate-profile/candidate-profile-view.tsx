"use client"

import * as React from "react"

import { Grid } from "@/components/layout/grid"
import { Stack } from "@/components/layout/stack"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { DashboardErrorState } from "@/features/dashboard"
import { useCandidateProfile } from "@/hooks"
import type { CandidateListItem, CandidateProfile } from "@/types"

import { CandidateProfileHeader } from "./candidate-profile-header"
import { CandidateProfileSidebar } from "./candidate-profile-sidebar"
import { CandidateSummaryCards } from "./candidate-summary-cards"
import { ActivityTab } from "./tabs/activity-tab"
import { AiMatchTab } from "./tabs/ai-match-tab"
import { CertificationsTab } from "./tabs/certifications-tab"
import { EducationTab } from "./tabs/education-tab"
import { ExperienceTab } from "./tabs/experience-tab"
import { NotesTab } from "./tabs/notes-tab"
import { OverviewTab } from "./tabs/overview-tab"
import { ProjectsTab } from "./tabs/projects-tab"
import { ResumeTab } from "./tabs/resume-tab"
import { SkillsTab } from "./tabs/skills-tab"
import { TasksTab } from "./tabs/tasks-tab"

export interface CandidateProfileViewProps {
  candidateId: string
}

/** Adapts the profile response into the shape CandidateActionsMenu (built for
 * the candidates table) expects — it only reads a handful of these fields;
 * the rest are unused placeholders required by the shared type. */
function toActionsMenuCandidate(profile: CandidateProfile): CandidateListItem {
  return {
    resume_file_id: profile.resume_file_id,
    candidate_id: profile.candidate_id,
    candidate_name: profile.candidate_name,
    email: profile.email,
    phone: profile.phone,
    location: profile.location,
    current_company: profile.current_company,
    current_role: profile.current_role,
    years_of_experience: profile.years_of_experience,
    skills: profile.structured_resume.skills,
    education: profile.structured_resume.education.map((e) => ({
      institution: e.institution,
      degree: e.degree,
      field: e.field,
    })),
    rank: null,
    overall_score: profile.overall_score,
    sub_scores: profile.sub_scores,
    recommendation: profile.recommendation,
    upload_status: profile.upload_status,
    review_status: profile.review_status,
    pipeline_stage: profile.pipeline_stage,
    assigned_recruiter: profile.assigned_recruiter,
    notes: null,
    applied_at: profile.uploaded_at,
  }
}

function CandidateProfileView({ candidateId }: CandidateProfileViewProps) {
  const [activeTab, setActiveTab] = React.useState("overview")
  const profileQuery = useCandidateProfile(candidateId)

  if (profileQuery.isPending) {
    return (
      <Stack gap="lg">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-96 w-full" />
      </Stack>
    )
  }

  if (profileQuery.isError) {
    return <DashboardErrorState error={profileQuery.error} onRetry={() => profileQuery.refetch()} />
  }

  const profile = profileQuery.data

  return (
    <Stack gap="lg">
      <CandidateProfileHeader
        profile={profile}
        actionsCandidate={toActionsMenuCandidate(profile)}
        onEditNotes={() => setActiveTab("notes")}
      />

      <CandidateSummaryCards overallScore={profile.overall_score} subScores={profile.sub_scores} />

      <Grid cols={1} colsLg={4} gap="lg">
        <div className="lg:col-span-1">
          <CandidateProfileSidebar profile={profile} />
        </div>

        <div className="lg:col-span-3">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="flex-wrap">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="resume">Resume</TabsTrigger>
              <TabsTrigger value="ai-match">AI Match Analysis</TabsTrigger>
              <TabsTrigger value="experience">Experience</TabsTrigger>
              <TabsTrigger value="skills">Skills</TabsTrigger>
              <TabsTrigger value="education">Education</TabsTrigger>
              <TabsTrigger value="projects">Projects</TabsTrigger>
              <TabsTrigger value="certifications">Certifications</TabsTrigger>
              <TabsTrigger value="activity">Activity</TabsTrigger>
              <TabsTrigger value="notes">Notes</TabsTrigger>
              <TabsTrigger value="tasks">Tasks</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="pt-4">
              <OverviewTab profile={profile} />
            </TabsContent>
            <TabsContent value="resume" className="pt-4">
              <ResumeTab profile={profile} />
            </TabsContent>
            <TabsContent value="ai-match" className="pt-4">
              <AiMatchTab candidateId={candidateId} />
            </TabsContent>
            <TabsContent value="experience" className="pt-4">
              <ExperienceTab experience={profile.structured_resume.experience} />
            </TabsContent>
            <TabsContent value="skills" className="pt-4">
              <SkillsTab candidateId={candidateId} skills={profile.structured_resume.skills} />
            </TabsContent>
            <TabsContent value="education" className="pt-4">
              <EducationTab education={profile.structured_resume.education} />
            </TabsContent>
            <TabsContent value="projects" className="pt-4">
              <ProjectsTab projects={profile.structured_resume.projects} />
            </TabsContent>
            <TabsContent value="certifications" className="pt-4">
              <CertificationsTab certifications={profile.structured_resume.certifications} />
            </TabsContent>
            <TabsContent value="activity" className="pt-4">
              <ActivityTab candidateId={candidateId} />
            </TabsContent>
            <TabsContent value="notes" className="pt-4">
              <NotesTab candidateId={candidateId} />
            </TabsContent>
            <TabsContent value="tasks" className="pt-4">
              <TasksTab candidateId={candidateId} />
            </TabsContent>
          </Tabs>
        </div>
      </Grid>
    </Stack>
  )
}

export { CandidateProfileView }
