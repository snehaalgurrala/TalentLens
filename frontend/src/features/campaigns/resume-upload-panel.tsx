"use client"

import * as React from "react"
import { FileText, Trash2 } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { FileUpload } from "@/components/ui/file-upload"
import { Progress } from "@/components/ui/progress"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { useDeleteResume, useResumes, useUploadResumes } from "@/hooks"
import type { ResumeFile, UploadStatus } from "@/types"

export interface ResumeUploadPanelProps {
  campaignId: string
}

const ACCEPT = ".pdf,.docx,.zip"

const STATUS_BADGE_VARIANT: Record<UploadStatus, React.ComponentProps<typeof Badge>["variant"]> = {
  PENDING: "secondary",
  UPLOADED: "secondary",
  PROCESSING: "pending",
  PARSED: "active",
  FAILED: "destructive",
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function ResumeUploadPanel({ campaignId }: ResumeUploadPanelProps) {
  const [stagedFiles, setStagedFiles] = React.useState<File[]>([])
  const [progress, setProgress] = React.useState<number | null>(null)

  const resumesQuery = useResumes(campaignId)
  const uploadResumes = useUploadResumes(campaignId)
  const deleteResume = useDeleteResume(campaignId)

  const resumes = resumesQuery.data ?? []
  const existingFilenames = React.useMemo(
    () => new Set(resumesQuery.data?.map((rf) => rf.original_filename.toLowerCase())),
    [resumesQuery.data]
  )
  const duplicateNames = stagedFiles
    .filter((file) => existingFilenames.has(file.name.toLowerCase()))
    .map((file) => file.name)

  function handleFilesSelected(files: File[]) {
    setStagedFiles((prev) => [...prev, ...files])
  }

  function handleFileRemove(file: File) {
    setStagedFiles((prev) => prev.filter((f) => f !== file))
  }

  async function handleUpload() {
    if (stagedFiles.length === 0) return
    setProgress(0)
    try {
      const result = await uploadResumes.mutateAsync({
        files: stagedFiles,
        onUploadProgress: setProgress,
      })
      const failedCount = stagedFiles.length - result.count
      toast.success(
        failedCount > 0
          ? `Uploaded ${result.count} file(s), ${failedCount} rejected`
          : `Uploaded ${result.count} file(s) — parsing started in the background`
      )
      setStagedFiles([])
    } catch (error) {
      const message = error instanceof Error ? error.message : "Upload failed"
      toast.error(message)
    } finally {
      setProgress(null)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Resume Upload</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <FileUpload
            accept={ACCEPT}
            multiple
            description="PDF, DOCX, or ZIP — up to 10MB per file"
            files={stagedFiles}
            onFilesSelected={handleFilesSelected}
            onFileRemove={handleFileRemove}
          />

          {duplicateNames.length > 0 && (
            <p className="text-caption text-warning-emphasis">
              Possible duplicates already in this campaign: {duplicateNames.join(", ")}
            </p>
          )}

          {progress !== null && <Progress value={progress} />}

          <Button
            onClick={handleUpload}
            disabled={stagedFiles.length === 0 || uploadResumes.isPending}
            isLoading={uploadResumes.isPending}
            className="self-start"
          >
            Upload {stagedFiles.length > 0 ? `${stagedFiles.length} file(s)` : ""}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Uploaded Resumes</CardTitle>
        </CardHeader>
        <CardContent>
          {resumesQuery.isPending ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : resumes.length === 0 ? (
            <TableEmptyState icon={FileText} title="No uploads yet" description="Uploaded resumes will appear here." />
          ) : (
            <ul className="flex flex-col gap-2">
              {resumes.map((resume: ResumeFile) => (
                <li
                  key={resume.id}
                  className="flex items-center gap-3 rounded-lg border border-border px-3 py-2"
                >
                  <FileText className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                  <div className="flex min-w-0 flex-1 flex-col">
                    <span className="truncate text-sm font-medium text-foreground">
                      {resume.original_filename}
                    </span>
                    <span className="text-caption text-muted-foreground">
                      {formatFileSize(resume.file_size)}
                      {resume.error_message ? ` — ${resume.error_message}` : ""}
                    </span>
                  </div>
                  <Badge variant={STATUS_BADGE_VARIANT[resume.upload_status]}>
                    {resume.upload_status}
                  </Badge>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label={`Delete ${resume.original_filename}`}
                    onClick={() => deleteResume.mutate(resume.id)}
                  >
                    <Trash2 className="size-4" aria-hidden="true" />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export { ResumeUploadPanel }
