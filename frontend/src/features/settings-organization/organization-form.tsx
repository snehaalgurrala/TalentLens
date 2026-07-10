"use client"

import * as React from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useUpdateOrganization } from "@/hooks"
import type { Organization, OrganizationUpdate } from "@/types"

import { OrganizationLogoUploader } from "./organization-logo-uploader"
import { organizationFormSchema, type OrganizationFormValues } from "./schemas"

export interface OrganizationFormProps {
  organization: Organization
}

function organizationToFormValues(organization: Organization): OrganizationFormValues {
  return {
    name: organization.name,
    industry: organization.industry ?? "",
    website: organization.website ?? "",
    company_email: organization.company_email ?? "",
    phone: organization.phone ?? "",
    address_line1: organization.address_line1 ?? "",
    address_line2: organization.address_line2 ?? "",
    city: organization.city ?? "",
    state: organization.state ?? "",
    postal_code: organization.postal_code ?? "",
    country: organization.country ?? "",
    timezone: organization.timezone ?? "",
    description: organization.description ?? "",
  }
}

function toPayload(values: OrganizationFormValues): OrganizationUpdate {
  return {
    name: values.name.trim(),
    industry: values.industry || undefined,
    website: values.website || undefined,
    company_email: values.company_email || undefined,
    phone: values.phone || undefined,
    address_line1: values.address_line1 || undefined,
    address_line2: values.address_line2 || undefined,
    city: values.city || undefined,
    state: values.state || undefined,
    postal_code: values.postal_code || undefined,
    country: values.country || undefined,
    timezone: values.timezone || undefined,
    description: values.description || undefined,
  }
}

function OrganizationForm({ organization }: OrganizationFormProps) {
  const updateOrganization = useUpdateOrganization()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<OrganizationFormValues>({
    resolver: zodResolver(organizationFormSchema),
    defaultValues: organizationToFormValues(organization),
  })

  React.useEffect(() => {
    reset(organizationToFormValues(organization))
  }, [organization, reset])

  async function onSubmit(values: OrganizationFormValues) {
    try {
      await updateOrganization.mutateAsync(toPayload(values))
      toast.success("Organization settings saved")
    } catch (error) {
      const message = error instanceof Error ? error.message : "Something went wrong"
      toast.error(message)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Organization Profile</CardTitle>
        <CardDescription>
          These details appear on candidate-facing pages and reports.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form noValidate onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-6">
          <OrganizationLogoUploader organization={organization} />

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5 sm:col-span-2">
              <Label htmlFor="org-name">Organization Name</Label>
              <Input id="org-name" aria-invalid={!!errors.name} {...register("name")} />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="org-industry">Industry</Label>
              <Input id="org-industry" {...register("industry")} />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="org-website">Website</Label>
              <Input id="org-website" placeholder="https://example.com" {...register("website")} />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="org-company-email">Company Email</Label>
              <Input
                id="org-company-email"
                type="email"
                aria-invalid={!!errors.company_email}
                {...register("company_email")}
              />
              {errors.company_email && (
                <p className="text-xs text-destructive">{errors.company_email.message}</p>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="org-phone">Phone</Label>
              <Input id="org-phone" {...register("phone")} />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="org-address-line1">Address Line 1</Label>
              <Input id="org-address-line1" {...register("address_line1")} />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="org-address-line2">Address Line 2</Label>
              <Input id="org-address-line2" {...register("address_line2")} />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="org-city">City</Label>
              <Input id="org-city" {...register("city")} />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="org-state">State</Label>
              <Input id="org-state" {...register("state")} />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="org-postal-code">Postal Code</Label>
              <Input id="org-postal-code" {...register("postal_code")} />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="org-country">Country</Label>
              <Input id="org-country" {...register("country")} />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="org-timezone">Timezone</Label>
              <Input id="org-timezone" placeholder="e.g. America/New_York" {...register("timezone")} />
            </div>

            <div className="flex flex-col gap-1.5 sm:col-span-2">
              <Label htmlFor="org-description">Description</Label>
              <Textarea id="org-description" rows={4} {...register("description")} />
            </div>
          </div>

          <div>
            <Button type="submit" isLoading={isSubmitting}>
              Save Changes
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

export { OrganizationForm }
