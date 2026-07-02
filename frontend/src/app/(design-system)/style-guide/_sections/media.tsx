"use client"

import * as React from "react"

import {
  Avatar,
  AvatarFallback,
  AvatarGroup,
  AvatarGroupCount,
  AvatarImage,
} from "@/components/ui/avatar"
import { FileUpload } from "@/components/ui/file-upload"
import { Row, Section } from "../_components/section"

function MediaSection() {
  const [files, setFiles] = React.useState<File[]>([])

  return (
    <Section
      id="media"
      title="Media & uploads"
      description="Avatars (with group/overflow count) and the drag-and-drop File Upload component."
    >
      <Row label="Avatar">
        <Avatar size="sm">
          <AvatarFallback>JD</AvatarFallback>
        </Avatar>
        <Avatar>
          <AvatarImage src="https://i.pravatar.cc/64?img=5" alt="" />
          <AvatarFallback>AO</AvatarFallback>
        </Avatar>
        <Avatar size="lg">
          <AvatarFallback>LC</AvatarFallback>
        </Avatar>
      </Row>

      <Row label="Avatar group">
        <AvatarGroup>
          <Avatar>
            <AvatarFallback>AO</AvatarFallback>
          </Avatar>
          <Avatar>
            <AvatarFallback>LC</AvatarFallback>
          </Avatar>
          <Avatar>
            <AvatarFallback>SR</AvatarFallback>
          </Avatar>
          <AvatarGroupCount>+4</AvatarGroupCount>
        </AvatarGroup>
      </Row>

      <Row label="File upload">
        <div className="w-full max-w-md">
          <FileUpload
            description="PDF or DOCX, up to 10MB"
            accept=".pdf,.docx"
            multiple
            files={files}
            onFilesSelected={(newFiles) =>
              setFiles((prev) => [...prev, ...newFiles])
            }
            onFileRemove={(file) =>
              setFiles((prev) => prev.filter((f) => f !== file))
            }
          />
        </div>
      </Row>
    </Section>
  )
}

export { MediaSection }
