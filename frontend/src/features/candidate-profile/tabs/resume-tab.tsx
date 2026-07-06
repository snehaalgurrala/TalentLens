"use client"

import * as React from "react"
import { Download, Maximize2 } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { candidateService } from "@/services/candidate.service"
import { downloadBlob } from "@/utils"
import type { CandidateProfile } from "@/types"

export interface ResumeTabProps {
  profile: CandidateProfile
}

function ResumeTab({ profile }: ResumeTabProps) {
  const [blobUrl, setBlobUrl] = React.useState<string | null>(null)
  const [filename, setFilename] = React.useState("resume")
  const [isLoading, setIsLoading] = React.useState(true)
  const [error, setError] = React.useState(false)

  React.useEffect(() => {
    let cancelled = false
    let objectUrl: string | null = null

    async function load() {
      setIsLoading(true)
      setError(false)
      try {
        const { blob, filename: name } = await candidateService.downloadResume(profile.resume_file_id)
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setBlobUrl(objectUrl)
        setFilename(name)
      } catch {
        if (!cancelled) setError(true)
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    void load()
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [profile.resume_file_id])

  async function handleDownload() {
    try {
      const { blob, filename: name } = await candidateService.downloadResume(profile.resume_file_id)
      downloadBlob(name, blob)
    } catch {
      toast.error("Failed to download resume")
    }
  }

  function handleOpenFullScreen() {
    if (blobUrl) window.open(blobUrl, "_blank", "noopener,noreferrer")
  }

  const structured = profile.structured_resume

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Resume Preview</CardTitle>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleOpenFullScreen} disabled={!blobUrl}>
              <Maximize2 aria-hidden="true" />
              Open Full Screen
            </Button>
            <Button size="sm" onClick={handleDownload}>
              <Download aria-hidden="true" />
              Download
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-[70vh] w-full" />
          ) : error ? (
            <p className="py-12 text-center text-sm text-muted-foreground">
              Couldn&rsquo;t load the resume preview. Try downloading it instead.
            </p>
          ) : (
            <object
              data={blobUrl ?? undefined}
              type="application/pdf"
              className="h-[70vh] w-full rounded-lg border border-border"
              aria-label={`${profile.candidate_name}'s resume`}
            >
              <p className="p-4 text-sm text-muted-foreground">
                Your browser can&rsquo;t preview this file inline.{" "}
                <button type="button" className="text-primary hover:underline" onClick={handleDownload}>
                  Download {filename}
                </button>
                .
              </p>
            </object>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Parsed Sections</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div>
            <p className="mb-1.5 text-caption font-medium text-muted-foreground">Skills</p>
            <div className="flex flex-wrap gap-1.5">
              {structured.skills.length > 0 ? (
                structured.skills.map((skill) => (
                  <Badge key={skill} variant="outline">
                    {skill}
                  </Badge>
                ))
              ) : (
                <span className="text-sm text-muted-foreground">—</span>
              )}
            </div>
          </div>
          <div>
            <p className="mb-1.5 text-caption font-medium text-muted-foreground">Education</p>
            {structured.education.length > 0 ? (
              <ul className="flex flex-col gap-1 text-sm text-foreground">
                {structured.education.map((edu, i) => (
                  <li key={i}>
                    {edu.degree ?? "Degree"} — {edu.institution ?? "Institution"}
                  </li>
                ))}
              </ul>
            ) : (
              <span className="text-sm text-muted-foreground">—</span>
            )}
          </div>
          <div>
            <p className="mb-1.5 text-caption font-medium text-muted-foreground">Experience</p>
            {structured.experience.length > 0 ? (
              <ul className="flex flex-col gap-1 text-sm text-foreground">
                {structured.experience.map((exp, i) => (
                  <li key={i}>
                    {exp.role ?? "Role"} — {exp.company ?? "Company"}
                  </li>
                ))}
              </ul>
            ) : (
              <span className="text-sm text-muted-foreground">—</span>
            )}
          </div>
          <p className="text-caption text-muted-foreground">
            These sections reflect what the AI parser extracted. In-document highlighting isn&rsquo;t
            available for the native PDF viewer used here.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

export { ResumeTab }
