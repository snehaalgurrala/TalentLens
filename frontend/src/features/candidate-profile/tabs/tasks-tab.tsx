"use client"

import * as React from "react"
import { Pencil, Trash2, UserCog } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { Textarea } from "@/components/ui/textarea"
import { Stack } from "@/components/layout/stack"
import { DashboardErrorState } from "@/features/dashboard"
import {
  useCandidateTasks,
  useCompleteCandidateTask,
  useCreateCandidateTask,
  useDeleteCandidateTask,
  useOrgMembers,
  useReassignCandidateTask,
  useUpdateCandidateTask,
} from "@/hooks"
import { formatDate } from "@/utils"
import type { CandidateTask, TaskPriority } from "@/types"

export interface TasksTabProps {
  candidateId: string
}

const UNASSIGNED = "__unassigned__"

const PRIORITY_OPTIONS: { value: TaskPriority; label: string }[] = [
  { value: "LOW", label: "Low" },
  { value: "MEDIUM", label: "Medium" },
  { value: "HIGH", label: "High" },
  { value: "URGENT", label: "Urgent" },
]

const PRIORITY_VARIANT: Record<TaskPriority, React.ComponentProps<typeof Badge>["variant"]> = {
  LOW: "secondary",
  MEDIUM: "outline",
  HIGH: "warning",
  URGENT: "rejected",
}

function TaskComposer({ candidateId }: { candidateId: string }) {
  const [title, setTitle] = React.useState("")
  const [description, setDescription] = React.useState("")
  const [dueDate, setDueDate] = React.useState("")
  const [priority, setPriority] = React.useState<TaskPriority>("MEDIUM")
  const [assigneeId, setAssigneeId] = React.useState(UNASSIGNED)
  const membersQuery = useOrgMembers()
  const createTask = useCreateCandidateTask(candidateId)

  function handleCreate() {
    createTask.mutate(
      {
        title: title.trim(),
        description: description.trim() || null,
        due_date: dueDate ? new Date(dueDate).toISOString() : null,
        priority,
        assignee_id: assigneeId === UNASSIGNED ? null : assigneeId,
      },
      {
        onSuccess: () => {
          setTitle("")
          setDescription("")
          setDueDate("")
          setPriority("MEDIUM")
          setAssigneeId(UNASSIGNED)
          toast.success("Task created")
        },
        onError: (error) => toast.error(error.message || "Failed to create task"),
      }
    )
  }

  return (
    <Card>
      <CardContent>
        <Stack gap="sm">
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Task title (e.g. Schedule interview)"
          />
          <Textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Description (optional)"
            className="min-h-16"
          />
          <div className="flex flex-wrap items-center gap-2">
            <Input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="w-40"
              aria-label="Due date"
            />
            <Select value={priority} onValueChange={(v) => setPriority(v as TaskPriority)}>
              <SelectTrigger className="w-32" aria-label="Priority">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PRIORITY_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={assigneeId} onValueChange={setAssigneeId}>
              <SelectTrigger className="w-48" aria-label="Assignee">
                <SelectValue placeholder="Unassigned" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={UNASSIGNED}>Unassigned</SelectItem>
                {(membersQuery.data ?? []).map((member) => (
                  <SelectItem key={member.id} value={member.id}>
                    {member.full_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              size="sm"
              className="ml-auto"
              onClick={handleCreate}
              disabled={!title.trim()}
              isLoading={createTask.isPending}
            >
              Add Task
            </Button>
          </div>
        </Stack>
      </CardContent>
    </Card>
  )
}

function TaskItem({ task, candidateId }: { task: CandidateTask; candidateId: string }) {
  const [isEditing, setIsEditing] = React.useState(false)
  const [title, setTitle] = React.useState(task.title)
  const [description, setDescription] = React.useState(task.description ?? "")
  const membersQuery = useOrgMembers()
  const updateTask = useUpdateCandidateTask(candidateId)
  const completeTask = useCompleteCandidateTask(candidateId)
  const reassignTask = useReassignCandidateTask(candidateId)
  const deleteTask = useDeleteCandidateTask(candidateId)

  const isCompleted = task.status === "COMPLETED"

  function handleToggleComplete() {
    if (isCompleted) return
    completeTask.mutate(task.id, {
      onSuccess: () => toast.success("Task completed"),
      onError: (error) => toast.error(error.message || "Failed to complete task"),
    })
  }

  function handleSaveEdit() {
    updateTask.mutate(
      { taskId: task.id, data: { title: title.trim(), description: description.trim() || null } },
      {
        onSuccess: () => {
          setIsEditing(false)
          toast.success("Task updated")
        },
        onError: (error) => toast.error(error.message || "Failed to update task"),
      }
    )
  }

  function handleReassign(value: string) {
    reassignTask.mutate(
      { taskId: task.id, assigneeId: value === UNASSIGNED ? null : value },
      {
        onSuccess: () => toast.success("Task reassigned"),
        onError: (error) => toast.error(error.message || "Failed to reassign task"),
      }
    )
  }

  function handleDelete() {
    deleteTask.mutate(task.id, {
      onSuccess: () => toast.success("Task deleted"),
      onError: (error) => toast.error(error.message || "Failed to delete task"),
    })
  }

  return (
    <Card>
      <CardContent className="flex flex-col gap-2">
        {isEditing ? (
          <Stack gap="sm">
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title" />
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description"
              className="min-h-16"
            />
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={() => setIsEditing(false)}>
                Cancel
              </Button>
              <Button size="sm" onClick={handleSaveEdit} isLoading={updateTask.isPending}>
                Save
              </Button>
            </div>
          </Stack>
        ) : (
          <>
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-start gap-2">
                <Checkbox
                  checked={isCompleted}
                  onCheckedChange={handleToggleComplete}
                  disabled={isCompleted || completeTask.isPending}
                  aria-label={`Mark "${task.title}" complete`}
                  className="mt-0.5"
                />
                <div className="flex flex-col gap-1">
                  <span
                    className={
                      isCompleted
                        ? "text-sm font-medium text-muted-foreground line-through"
                        : "text-sm font-medium text-foreground"
                    }
                  >
                    {task.title}
                  </span>
                  {task.description && (
                    <p className="text-caption text-muted-foreground">{task.description}</p>
                  )}
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={PRIORITY_VARIANT[task.priority]}>{task.priority}</Badge>
                    {task.due_date && (
                      <span className="text-caption text-muted-foreground">Due {formatDate(task.due_date)}</span>
                    )}
                    <span className="text-caption text-muted-foreground">
                      {task.assignee?.full_name ?? "Unassigned"}
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <Select value={task.assignee?.id ?? UNASSIGNED} onValueChange={handleReassign}>
                  <SelectTrigger className="w-8 border-none p-0" aria-label="Reassign task">
                    <UserCog className="size-3.5" aria-hidden="true" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={UNASSIGNED}>Unassigned</SelectItem>
                    {(membersQuery.data ?? []).map((member) => (
                      <SelectItem key={member.id} value={member.id}>
                        {member.full_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button variant="ghost" size="icon-sm" aria-label="Edit task" onClick={() => setIsEditing(true)}>
                  <Pencil className="size-3.5" aria-hidden="true" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label="Delete task"
                  onClick={handleDelete}
                  disabled={deleteTask.isPending}
                >
                  <Trash2 className="size-3.5" aria-hidden="true" />
                </Button>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

function TasksTab({ candidateId }: TasksTabProps) {
  const tasksQuery = useCandidateTasks(candidateId)

  const tasks = tasksQuery.data ?? []
  const openTasks = tasks.filter((t) => t.status !== "COMPLETED")
  const completedTasks = tasks.filter((t) => t.status === "COMPLETED")

  return (
    <Stack gap="lg">
      <TaskComposer candidateId={candidateId} />

      {tasksQuery.isPending ? (
        <Stack gap="sm">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </Stack>
      ) : tasksQuery.isError ? (
        <DashboardErrorState error={tasksQuery.error} onRetry={() => tasksQuery.refetch()} />
      ) : tasks.length === 0 ? (
        <TableEmptyState title="No tasks yet" description="Create the first follow-up task for this candidate." />
      ) : (
        <Stack gap="lg">
          <Stack gap="sm">
            {openTasks.map((task) => (
              <TaskItem key={task.id} task={task} candidateId={candidateId} />
            ))}
            {openTasks.length === 0 && (
              <p className="text-caption text-muted-foreground">No open tasks.</p>
            )}
          </Stack>
          {completedTasks.length > 0 && (
            <Stack gap="sm">
              <span className="text-caption font-medium text-muted-foreground">
                Completed ({completedTasks.length})
              </span>
              {completedTasks.map((task) => (
                <TaskItem key={task.id} task={task} candidateId={candidateId} />
              ))}
            </Stack>
          )}
        </Stack>
      )}
    </Stack>
  )
}

export { TasksTab }
