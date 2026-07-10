"use client"

import * as React from "react"
import { toast } from "sonner"

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { FileUpload } from "@/components/ui/file-upload"
import { useUploadOrganizationLogo } from "@/hooks"
import { organizationService } from "@/services/organization.service"
import type { Organization } from "@/types"

export interface OrganizationLogoUploaderProps {
  organization: Organization
}

function OrganizationLogoUploader({ organization }: OrganizationLogoUploaderProps) {
  const uploadLogo = useUploadOrganizationLogo()
  const [logoObjectUrl, setLogoObjectUrl] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (!organization.logo_url) {
      setLogoObjectUrl(null)
      return
    }

    let cancelled = false
    let objectUrl: string | null = null

    organizationService
      .getLogoObjectUrl()
      .then((url) => {
        if (cancelled) {
          URL.revokeObjectURL(url)
          return
        }
        objectUrl = url
        setLogoObjectUrl(url)
      })
      .catch(() => {
        if (!cancelled) setLogoObjectUrl(null)
      })

    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [organization.logo_url])

  async function handleFilesSelected(files: File[]) {
    const file = files[0]
    if (!file) return
    try {
      await uploadLogo.mutateAsync(file)
      toast.success("Logo updated")
    } catch (error) {
      const message = error instanceof Error ? error.message : "Something went wrong"
      toast.error(message)
    }
  }

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
      <Avatar size="lg">
        {logoObjectUrl && <AvatarImage src={logoObjectUrl} alt={organization.name} />}
        <AvatarFallback className="text-base">
          {organization.name.slice(0, 2).toUpperCase()}
        </AvatarFallback>
      </Avatar>
      <div className="flex-1">
        <FileUpload
          accept="image/png,image/jpeg,image/svg+xml,image/webp"
          description="PNG, JPG, SVG or WEBP"
          disabled={uploadLogo.isPending}
          onFilesSelected={handleFilesSelected}
        />
      </div>
    </div>
  )
}

export { OrganizationLogoUploader }
