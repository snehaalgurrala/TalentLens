"use client"

import { Link as LinkIcon, Mail, MapPin, Phone } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Grid } from "@/components/layout/grid"
import type { CandidateProfile } from "@/types"

export interface OverviewTabProps {
  profile: CandidateProfile
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-caption text-muted-foreground">{label}</span>
      <span className="text-sm text-foreground">{value ?? "—"}</span>
    </div>
  )
}

function OverviewTab({ profile }: OverviewTabProps) {
  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Personal Information</CardTitle>
        </CardHeader>
        <CardContent>
          <Grid cols={2} colsSm={3} gap="md">
            <Field label="Email" value={profile.email} />
            <Field label="Phone" value={profile.phone} />
            <Field label="Location" value={profile.location} />
            <Field label="Current Employer" value={profile.current_company} />
            <Field label="Current Role" value={profile.current_role} />
            <Field
              label="Experience"
              value={profile.years_of_experience !== null ? `${profile.years_of_experience} yrs` : null}
            />
          </Grid>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Contact &amp; Social Links</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          <div className="flex items-center gap-2 text-sm text-foreground">
            <Mail className="size-4 text-muted-foreground" aria-hidden="true" />
            {profile.email ?? "—"}
          </div>
          <div className="flex items-center gap-2 text-sm text-foreground">
            <Phone className="size-4 text-muted-foreground" aria-hidden="true" />
            {profile.phone ?? "—"}
          </div>
          <div className="flex items-center gap-2 text-sm text-foreground">
            <LinkIcon className="size-4 text-muted-foreground" aria-hidden="true" />
            {profile.linkedin_url ? (
              <a href={profile.linkedin_url} target="_blank" rel="noreferrer" className="text-primary hover:underline">
                {profile.linkedin_url}
              </a>
            ) : (
              "—"
            )}
          </div>
          <div className="flex items-center gap-2 text-sm text-foreground">
            <LinkIcon className="size-4 text-muted-foreground" aria-hidden="true" />
            {profile.github_url ? (
              <a href={profile.github_url} target="_blank" rel="noreferrer" className="text-primary hover:underline">
                {profile.github_url}
              </a>
            ) : (
              "—"
            )}
          </div>
          <div className="flex items-center gap-2 text-sm text-foreground">
            <MapPin className="size-4 text-muted-foreground" aria-hidden="true" />
            {profile.location ?? "—"}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Compensation &amp; Preferences</CardTitle>
        </CardHeader>
        <CardContent>
          <Grid cols={2} colsSm={3} gap="md">
            <Field label="Current CTC" value={null} />
            <Field label="Expected CTC" value={null} />
            <Field label="Notice Period" value={null} />
            <Field label="Preferred Location" value={null} />
            <Field label="Employment Type" value={null} />
            <Field label="Languages" value={null} />
          </Grid>
          <p className="mt-3 text-caption text-muted-foreground">
            These fields aren&rsquo;t captured by resume parsing yet, so they show as unavailable rather
            than a guessed value.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

export { OverviewTab }
