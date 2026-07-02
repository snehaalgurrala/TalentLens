"use client"

import * as React from "react"
import { Download, FileText, Trash2, Upload } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { FileUpload } from "@/components/ui/file-upload"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { Textarea } from "@/components/ui/textarea"
import {
  useCreateJobDescriptionText,
  useDeleteJobDescription,
  useDownloadJobDescription,
  useJobDescriptions,
  useUploadJobDescription,
} from "@/hooks"
import { downloadBlob, formatDateTime } from "@/utils"
import type { EmbeddingStatus, JobDescription, ParsingStatus } from "@/types"

export interface JdPanelProps {
  campaignId: string
}

const PARSING_BADGE_VARIANT: Record<ParsingStatus, React.ComponentProps<typeof Badge>["variant"]> = {
  PENDING: "secondary",
  PROCESSING: "pending",
  COMPLETED: "active",
  FAILED: "destructive",
}

const EMBEDDING_BADGE_VARIANT: Record<EmbeddingStatus, React.ComponentProps<typeof Badge>["variant"]> = {
  PENDING: "secondary",
  GENERATING: "pending",
  READY: "active",
  FAILED: "destructive",
}

function JdUploadDialog({
  campaignId,
  open,
  onOpenChange,
  isReplace,
}: {
  campaignId: string
  open: boolean
  onOpenChange: (open: boolean) => void
  isReplace: boolean
}) {
  const [text, setText] = React.useState("")
  const [file, setFile] = React.useState<File | null>(null)
  const createFromText = useCreateJobDescriptionText(campaignId)
  const uploadFile = useUploadJobDescription(campaignId)
  const isPending = createFromText.isPending || uploadFile.isPending

  async function handleSubmitText() {
    try {
      await createFromText.mutateAsync({ text })
      toast.success(isReplace ? "Job description replaced" : "Job description added — parsing started")
      setText("")
      onOpenChange(false)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to save job description")
    }
  }

  async function handleSubmitFile() {
    if (!file) return
    try {
      await uploadFile.mutateAsync(file)
      toast.success(isReplace ? "Job description replaced" : "Job description uploaded — parsing started")
      setFile(null)
      onOpenChange(false)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to upload job description")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{isReplace ? "Replace Job Description" : "Add Job Description"}</DialogTitle>
        </DialogHeader>
        <Tabs defaultValue="text">
          <TabsList>
            <TabsTrigger value="text">Paste Text</TabsTrigger>
            <TabsTrigger value="file">Upload File</TabsTrigger>
          </TabsList>
          <TabsContent value="text" className="flex flex-col gap-3">
            <Textarea
              rows={10}
              placeholder="Paste the job description text here..."
              value={text}
              onChange={(event) => setText(event.target.value)}
            />
            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button onClick={handleSubmitText} disabled={!text.trim()} isLoading={isPending}>
                Save
              </Button>
            </DialogFooter>
          </TabsContent>
          <TabsContent value="file" className="flex flex-col gap-3">
            <FileUpload
              accept=".pdf,.docx"
              description="PDF or DOCX — up to 10MB"
              files={file ? [file] : []}
              onFilesSelected={(files) => setFile(files[0] ?? null)}
              onFileRemove={() => setFile(null)}
            />
            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button onClick={handleSubmitFile} disabled={!file} isLoading={isPending}>
                Upload
              </Button>
            </DialogFooter>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}

function StructuredJdPreview({ jd }: { jd: JobDescription }) {
  if (!jd.structured_json) return null
  const entries = Object.entries(jd.structured_json).filter(
    ([, value]) => value !== null && value !== undefined && (!Array.isArray(value) || value.length > 0)
  )
  if (entries.length === 0) return null

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border bg-muted/30 p-3">
      <p className="text-caption font-medium text-foreground">AI Extracted Information</p>
      <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {entries.map(([key, value]) => (
          <div key={key} className="flex flex-col gap-0.5">
            <dt className="text-caption text-muted-foreground capitalize">
              {key.replace(/_/g, " ")}
            </dt>
            <dd className="text-sm text-foreground">
              {Array.isArray(value) ? value.join(", ") : String(value)}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

function JdPanel({ campaignId }: JdPanelProps) {
  const [dialogOpen, setDialogOpen] = React.useState(false)
  const [isReplaceFlow, setIsReplaceFlow] = React.useState(false)

  const jdQuery = useJobDescriptions(campaignId)
  const deleteJd = useDeleteJobDescription(campaignId)
  const downloadJd = useDownloadJobDescription()

  const jobDescriptions = jdQuery.data ?? []
  const current = jobDescriptions[0]
  const history = jobDescriptions.slice(1)

  async function handleReplace() {
    if (current) {
      try {
        await deleteJd.mutateAsync(current.id)
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Failed to replace job description")
        return
      }
    }
    setIsReplaceFlow(true)
    setDialogOpen(true)
  }

  async function handleDownload(jd: JobDescription) {
    try {
      const blob = await downloadJd.mutateAsync(jd.id)
      downloadBlob(jd.original_filename ?? "job-description", blob)
    } catch {
      toast.error("This job description has no source file to download.")
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Job Description</CardTitle>
          {current && (
            <div className="flex gap-2">
              {current.storage_path && (
                <Button variant="outline" size="sm" onClick={() => handleDownload(current)}>
                  <Download className="size-4" aria-hidden="true" />
                  Download
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={handleReplace}>
                <Upload className="size-4" aria-hidden="true" />
                Replace
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="Delete job description"
                onClick={() => deleteJd.mutate(current.id)}
              >
                <Trash2 className="size-4" aria-hidden="true" />
              </Button>
            </div>
          )}
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {jdQuery.isPending ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : !current ? (
            <TableEmptyState
              icon={FileText}
              title="No job description yet"
              description="Add a job description so candidates can be ranked against it."
              action={
                <Button
                  size="sm"
                  onClick={() => {
                    setIsReplaceFlow(false)
                    setDialogOpen(true)
                  }}
                >
                  Add Job Description
                </Button>
              }
            />
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-foreground">
                  {current.original_filename ?? "Pasted text"}
                </span>
                <Badge variant={PARSING_BADGE_VARIANT[current.parsing_status]}>
                  Parsing: {current.parsing_status}
                </Badge>
                <Badge variant={EMBEDDING_BADGE_VARIANT[current.embedding_status]}>
                  Embedding: {current.embedding_status}
                </Badge>
                <span className="text-caption text-muted-foreground">
                  Added {formatDateTime(current.created_at)}
                </span>
              </div>

              {current.parsing_error && (
                <p className="text-caption text-destructive-emphasis">{current.parsing_error}</p>
              )}

              <div className="max-h-48 overflow-y-auto rounded-lg border border-border bg-muted/20 p-3 text-sm whitespace-pre-wrap text-foreground">
                {current.raw_text}
              </div>

              <StructuredJdPreview jd={current} />
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Version History</CardTitle>
        </CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Previous job description versions will appear here after a replacement.
            </p>
          ) : (
            <ul className="flex flex-col gap-2">
              {history.map((jd) => (
                <li
                  key={jd.id}
                  className="flex items-center justify-between rounded-lg border border-border px-3 py-2 text-sm"
                >
                  <span className="text-foreground">{jd.original_filename ?? "Pasted text"}</span>
                  <span className="text-caption text-muted-foreground">
                    {formatDateTime(jd.created_at)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <JdUploadDialog
        campaignId={campaignId}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        isReplace={isReplaceFlow}
      />
    </div>
  )
}

export { JdPanel }
