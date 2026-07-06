"use client"

import { Users } from "lucide-react"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { Stack } from "@/components/layout/stack"
import { DashboardErrorState } from "@/features/dashboard"
import { useRecruiterWorkload } from "@/hooks"
import { initialsFromName } from "@/utils"

import { PIPELINE_STAGE_LABELS } from "@/features/candidates/constants"

function RecruiterWorkloadPanel() {
  const workloadQuery = useRecruiterWorkload()

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Users className="size-3.5" aria-hidden="true" />
          Workload
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Recruiter Workload</DialogTitle>
        </DialogHeader>

        {workloadQuery.isPending ? (
          <Stack gap="sm">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </Stack>
        ) : workloadQuery.isError ? (
          <DashboardErrorState error={workloadQuery.error} onRetry={() => workloadQuery.refetch()} />
        ) : workloadQuery.data.items.length === 0 ? (
          <TableEmptyState title="No recruiters yet" description="Invite recruiters to see their workload here." />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Recruiter</TableHead>
                <TableHead className="text-center">Total Assigned</TableHead>
                <TableHead>By Stage</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {workloadQuery.data.items.map((item) => (
                <TableRow key={item.recruiter.id}>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Avatar size="sm">
                        <AvatarFallback>{initialsFromName(item.recruiter.full_name)}</AvatarFallback>
                      </Avatar>
                      <span>{item.recruiter.full_name}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-center tabular-nums font-medium">
                    {item.total_assigned}
                  </TableCell>
                  <TableCell>
                    {item.by_stage.length === 0 ? (
                      <span className="text-muted-foreground">—</span>
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {item.by_stage.map((stage) => (
                          <Badge key={stage.pipeline_stage} variant="outline">
                            {PIPELINE_STAGE_LABELS[stage.pipeline_stage]}: {stage.count}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DialogContent>
    </Dialog>
  )
}

export { RecruiterWorkloadPanel }
