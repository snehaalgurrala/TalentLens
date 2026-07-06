"use client"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import type { StructuredProjectItem } from "@/types"

export interface ProjectsTabProps {
  projects: StructuredProjectItem[]
}

function ProjectsTab({ projects }: ProjectsTabProps) {
  if (projects.length === 0) {
    return (
      <TableEmptyState
        title="No projects parsed"
        description="This resume didn't include a recognizable projects section."
      />
    )
  }

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {projects.map((project, index) => (
        <Card key={index}>
          <CardHeader>
            <CardTitle>{project.name ?? "Untitled project"}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {project.description && <p className="text-sm text-foreground">{project.description}</p>}
            {project.technologies.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {project.technologies.map((tech) => (
                  <Badge key={tech} variant="outline">
                    {tech}
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export { ProjectsTab }
