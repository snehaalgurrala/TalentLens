"use client"

import * as React from "react"
import { ArrowDownAZ, ArrowUpAZ, AtSign, Bold, Italic, List, Pencil, Pin, PinOff, Trash2 } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { TableEmptyState } from "@/components/ui/table-empty-state"
import { Textarea } from "@/components/ui/textarea"
import { Stack } from "@/components/layout/stack"
import { DashboardErrorState } from "@/features/dashboard"
import {
  useCandidateNotes,
  useCreateCandidateNote,
  useDeleteCandidateNote,
  useOrgMembers,
  usePinCandidateNote,
  useUpdateCandidateNote,
} from "@/hooks"
import { formatDateTime } from "@/utils"
import type { CandidateNote, UserSummary } from "@/types"

import { renderNoteBody, resolveMentions } from "./notes-rich-text"

export interface NotesTabProps {
  candidateId: string
}

const ALL_RECRUITERS = "__all__"

function wrapSelection(
  textarea: HTMLTextAreaElement | null,
  value: string,
  onChange: (v: string) => void,
  token: string
) {
  if (!textarea) {
    onChange(`${value}${token}${token}`)
    return
  }
  const start = textarea.selectionStart ?? value.length
  const end = textarea.selectionEnd ?? value.length
  const selected = value.slice(start, end)
  const next = value.slice(0, start) + token + selected + token + value.slice(end)
  onChange(next)
  requestAnimationFrame(() => {
    textarea.focus()
    const cursor = start + token.length + selected.length + token.length
    textarea.setSelectionRange(cursor, cursor)
  })
}

function insertBulletLine(
  textarea: HTMLTextAreaElement | null,
  value: string,
  onChange: (v: string) => void
) {
  const prefix = value.length > 0 && !value.endsWith("\n") ? "\n- " : "- "
  if (!textarea) {
    onChange(`${value}${prefix}`)
    return
  }
  const start = textarea.selectionStart ?? value.length
  const next = value.slice(0, start) + prefix + value.slice(start)
  onChange(next)
  requestAnimationFrame(() => {
    textarea.focus()
    const cursor = start + prefix.length
    textarea.setSelectionRange(cursor, cursor)
  })
}

function NoteComposer({
  value,
  onChange,
  onSubmit,
  isSubmitting,
  submitLabel,
  onCancel,
  members,
}: {
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  isSubmitting: boolean
  submitLabel: string
  onCancel?: () => void
  members: UserSummary[]
}) {
  const textareaRef = React.useRef<HTMLTextAreaElement>(null)

  function insertMention(name: string) {
    const textarea = textareaRef.current
    const mention = `@${name} `
    if (!textarea) {
      onChange(`${value}${mention}`)
      return
    }
    const start = textarea.selectionStart ?? value.length
    const end = textarea.selectionEnd ?? value.length
    const next = value.slice(0, start) + mention + value.slice(end)
    onChange(next)
    requestAnimationFrame(() => {
      textarea.focus()
      const cursor = start + mention.length
      textarea.setSelectionRange(cursor, cursor)
    })
  }

  return (
    <Stack gap="sm">
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Add a note about this candidate… (supports **bold**, *italic*, - bullets)"
        className="min-h-24"
      />
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon-sm"
            aria-label="Bold"
            onClick={() => wrapSelection(textareaRef.current, value, onChange, "**")}
          >
            <Bold className="size-3.5" aria-hidden="true" />
          </Button>
          <Button
            variant="outline"
            size="icon-sm"
            aria-label="Italic"
            onClick={() => wrapSelection(textareaRef.current, value, onChange, "*")}
          >
            <Italic className="size-3.5" aria-hidden="true" />
          </Button>
          <Button
            variant="outline"
            size="icon-sm"
            aria-label="Bullet list"
            onClick={() => insertBulletLine(textareaRef.current, value, onChange)}
          >
            <List className="size-3.5" aria-hidden="true" />
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <AtSign aria-hidden="true" />
                Mention
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              {members.map((member) => (
                <DropdownMenuItem key={member.id} onSelect={() => insertMention(member.full_name)}>
                  {member.full_name}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <div className="flex items-center gap-2">
          {onCancel && (
            <Button variant="ghost" size="sm" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button
            size="sm"
            onClick={onSubmit}
            disabled={!value.trim()}
            isLoading={isSubmitting}
          >
            {submitLabel}
          </Button>
        </div>
      </div>
    </Stack>
  )
}

function NoteItem({
  note,
  candidateId,
  members,
}: {
  note: CandidateNote
  candidateId: string
  members: UserSummary[]
}) {
  const [isEditing, setIsEditing] = React.useState(false)
  const [draft, setDraft] = React.useState(note.body)
  const updateNote = useUpdateCandidateNote(candidateId)
  const deleteNote = useDeleteCandidateNote(candidateId)
  const pinNote = usePinCandidateNote(candidateId)

  function handleSave() {
    const mentionedUserIds = resolveMentions(draft, members)
    updateNote.mutate(
      { noteId: note.id, body: draft, mentionedUserIds },
      {
        onSuccess: () => {
          setIsEditing(false)
          toast.success("Note updated")
        },
        onError: (error) => toast.error(error.message || "Failed to update note"),
      }
    )
  }

  function handleDelete() {
    deleteNote.mutate(note.id, {
      onSuccess: () => toast.success("Note deleted"),
      onError: (error) => toast.error(error.message || "Failed to delete note"),
    })
  }

  function handleTogglePin() {
    pinNote.mutate(
      { noteId: note.id, isPinned: !note.is_pinned },
      {
        onError: (error) => toast.error(error.message || "Failed to update pin"),
      }
    )
  }

  if (isEditing) {
    return (
      <Card>
        <CardContent>
          <NoteComposer
            value={draft}
            onChange={setDraft}
            onSubmit={handleSave}
            isSubmitting={updateNote.isPending}
            submitLabel="Save"
            onCancel={() => {
              setDraft(note.body)
              setIsEditing(false)
            }}
            members={members}
          />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardContent className="flex flex-col gap-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex flex-col gap-0.5">
            <span className="flex items-center gap-1.5 text-sm font-medium text-foreground">
              {note.is_pinned && <Pin className="size-3.5 text-primary" aria-hidden="true" />}
              {note.author?.full_name ?? "Unknown"}
            </span>
            <span className="text-caption text-muted-foreground">{formatDateTime(note.created_at)}</span>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={note.is_pinned ? "Unpin note" : "Pin note"}
              onClick={handleTogglePin}
              disabled={pinNote.isPending}
            >
              {note.is_pinned ? (
                <PinOff className="size-3.5" aria-hidden="true" />
              ) : (
                <Pin className="size-3.5" aria-hidden="true" />
              )}
            </Button>
            {note.can_edit && (
              <>
                <Button variant="ghost" size="icon-sm" aria-label="Edit note" onClick={() => setIsEditing(true)}>
                  <Pencil className="size-3.5" aria-hidden="true" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label="Delete note"
                  onClick={handleDelete}
                  disabled={deleteNote.isPending}
                >
                  <Trash2 className="size-3.5" aria-hidden="true" />
                </Button>
              </>
            )}
          </div>
        </div>
        <div
          className="text-sm text-foreground [&_ul]:list-disc [&_ul]:pl-5 [&_p]:mb-1 [&_p:last-child]:mb-0"
          dangerouslySetInnerHTML={{ __html: renderNoteBody(note.body) }}
        />
      </CardContent>
    </Card>
  )
}

function NotesTab({ candidateId }: NotesTabProps) {
  const [draft, setDraft] = React.useState("")
  const [recruiterFilter, setRecruiterFilter] = React.useState(ALL_RECRUITERS)
  const [sortNewestFirst, setSortNewestFirst] = React.useState(true)
  const notesQuery = useCandidateNotes(candidateId)
  const createNote = useCreateCandidateNote(candidateId)
  const membersQuery = useOrgMembers()
  const members = membersQuery.data ?? []

  function handleCreate() {
    const mentionedUserIds = resolveMentions(draft, members)
    createNote.mutate(
      { body: draft, mentionedUserIds },
      {
        onSuccess: () => {
          setDraft("")
          toast.success("Note added")
        },
        onError: (error) => toast.error(error.message || "Failed to add note"),
      }
    )
  }

  const notes = React.useMemo(() => notesQuery.data ?? [], [notesQuery.data])
  const authors = React.useMemo(() => {
    const seen = new Map<string, UserSummary>()
    for (const note of notes) {
      if (note.author && !seen.has(note.author.id)) seen.set(note.author.id, note.author)
    }
    return Array.from(seen.values())
  }, [notes])

  const visibleNotes = React.useMemo(() => {
    const filtered =
      recruiterFilter === ALL_RECRUITERS
        ? notes
        : notes.filter((note) => note.author?.id === recruiterFilter)
    return [...filtered].sort((a, b) => {
      if (a.is_pinned !== b.is_pinned) return a.is_pinned ? -1 : 1
      const diff = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      return sortNewestFirst ? -diff : diff
    })
  }, [notes, recruiterFilter, sortNewestFirst])

  return (
    <Stack gap="lg">
      <Card>
        <CardContent>
          <NoteComposer
            value={draft}
            onChange={setDraft}
            onSubmit={handleCreate}
            isSubmitting={createNote.isPending}
            submitLabel="Add Note"
            members={members}
          />
        </CardContent>
      </Card>

      {notes.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Select value={recruiterFilter} onValueChange={setRecruiterFilter}>
            <SelectTrigger className="w-56" aria-label="Filter by recruiter">
              <SelectValue placeholder="All recruiters" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_RECRUITERS}>All recruiters</SelectItem>
              {authors.map((author) => (
                <SelectItem key={author.id} value={author.id}>
                  {author.full_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={() => setSortNewestFirst((v) => !v)}>
            {sortNewestFirst ? (
              <ArrowDownAZ className="size-3.5" aria-hidden="true" />
            ) : (
              <ArrowUpAZ className="size-3.5" aria-hidden="true" />
            )}
            {sortNewestFirst ? "Newest first" : "Oldest first"}
          </Button>
        </div>
      )}

      {notesQuery.isPending ? (
        <Stack gap="sm">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </Stack>
      ) : notesQuery.isError ? (
        <DashboardErrorState error={notesQuery.error} onRetry={() => notesQuery.refetch()} />
      ) : visibleNotes.length === 0 ? (
        <TableEmptyState title="No notes yet" description="Add the first note about this candidate." />
      ) : (
        <Stack gap="sm">
          {visibleNotes.map((note) => (
            <NoteItem key={note.id} note={note} candidateId={candidateId} members={members} />
          ))}
        </Stack>
      )}
    </Stack>
  )
}

export { NotesTab }
