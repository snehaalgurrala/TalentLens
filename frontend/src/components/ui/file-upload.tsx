"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { FileText, UploadCloud, X } from "lucide-react"

import { cn } from "@/lib/utils"

const dropzoneVariants = cva(
  "flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed px-6 py-10 text-center transition-colors outline-none",
  {
    variants: {
      state: {
        idle: "border-input bg-transparent hover:bg-muted/50",
        dragging: "border-primary bg-primary/5",
        error: "border-destructive bg-destructive/5",
        disabled: "cursor-not-allowed border-input bg-muted/30 opacity-50",
      },
    },
    defaultVariants: {
      state: "idle",
    },
  }
)

export interface FileUploadProps
  extends VariantProps<typeof dropzoneVariants> {
  accept?: string
  multiple?: boolean
  disabled?: boolean
  error?: string
  description?: string
  files?: File[]
  onFilesSelected: (files: File[]) => void
  onFileRemove?: (file: File) => void
  className?: string
}

function FileUpload({
  accept,
  multiple = false,
  disabled = false,
  error,
  description,
  files = [],
  onFilesSelected,
  onFileRemove,
  className,
}: FileUploadProps) {
  const [isDragging, setIsDragging] = React.useState(false)
  const inputId = React.useId()
  const descriptionId = React.useId()
  const inputRef = React.useRef<HTMLInputElement>(null)

  const state = disabled
    ? "disabled"
    : error
      ? "error"
      : isDragging
        ? "dragging"
        : "idle"

  function handleFiles(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return
    onFilesSelected(Array.from(fileList))
  }

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <div
        className={cn(dropzoneVariants({ state }))}
        onDragOver={(event) => {
          if (disabled) return
          event.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={(event) => {
          event.preventDefault()
          setIsDragging(false)
        }}
        onDrop={(event) => {
          event.preventDefault()
          setIsDragging(false)
          if (disabled) return
          handleFiles(event.dataTransfer.files)
        }}
      >
        <UploadCloud
          className={cn(
            "size-8",
            state === "error" ? "text-destructive" : "text-muted-foreground"
          )}
          aria-hidden="true"
        />
        <label htmlFor={inputId} className="text-sm text-foreground">
          <span className="font-medium text-primary underline-offset-4 hover:underline">
            Click to upload
          </span>{" "}
          or drag and drop
        </label>
        {description && (
          <p id={descriptionId} className="text-caption text-muted-foreground">
            {description}
          </p>
        )}
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          className="sr-only"
          accept={accept}
          multiple={multiple}
          disabled={disabled}
          aria-describedby={description ? descriptionId : undefined}
          onChange={(event) => {
            handleFiles(event.target.files)
            event.target.value = ""
          }}
        />
      </div>

      {error && <p className="text-caption text-destructive-emphasis">{error}</p>}

      {files.length > 0 && (
        <ul className="flex flex-col gap-1.5">
          {files.map((file, index) => (
            <li
              key={`${file.name}-${index}`}
              className="flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-2 text-sm"
            >
              <FileText
                className="size-4 shrink-0 text-muted-foreground"
                aria-hidden="true"
              />
              <span className="flex-1 truncate">{file.name}</span>
              <span className="shrink-0 text-caption text-muted-foreground">
                {(file.size / 1024).toFixed(0)} KB
              </span>
              {onFileRemove && (
                <button
                  type="button"
                  onClick={() => onFileRemove(file)}
                  className="shrink-0 text-muted-foreground transition-colors hover:text-destructive-emphasis"
                  aria-label={`Remove ${file.name}`}
                >
                  <X className="size-4" aria-hidden="true" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export { FileUpload }
