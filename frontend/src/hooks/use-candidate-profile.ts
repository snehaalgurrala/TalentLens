import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { candidateService } from "@/services/candidate.service"
import type {
  ApiError,
  CandidateActivity,
  CandidateMatchAnalysis,
  CandidateNote,
  CandidateProfile,
} from "@/types"

export const candidateProfileKeys = {
  all: ["candidate-profile"] as const,
  profile: (id: string) => [...candidateProfileKeys.all, "profile", id] as const,
  matchAnalysis: (id: string) => [...candidateProfileKeys.all, "match-analysis", id] as const,
  notes: (id: string) => [...candidateProfileKeys.all, "notes", id] as const,
  activity: (id: string) => [...candidateProfileKeys.all, "activity", id] as const,
}

export function useCandidateProfile(id: string | undefined) {
  return useQuery<CandidateProfile, ApiError>({
    queryKey: candidateProfileKeys.profile(id ?? ""),
    queryFn: () => candidateService.getProfile(id as string),
    enabled: Boolean(id),
  })
}

export function useCandidateMatchAnalysis(id: string | undefined) {
  return useQuery<CandidateMatchAnalysis, ApiError>({
    queryKey: candidateProfileKeys.matchAnalysis(id ?? ""),
    queryFn: () => candidateService.getMatchAnalysis(id as string),
    enabled: Boolean(id),
    retry: false,
  })
}

export function useCandidateNotes(id: string | undefined) {
  return useQuery<CandidateNote[], ApiError>({
    queryKey: candidateProfileKeys.notes(id ?? ""),
    queryFn: () => candidateService.listNotes(id as string),
    enabled: Boolean(id),
  })
}

export function useCandidateActivity(id: string | undefined) {
  return useQuery<CandidateActivity[], ApiError>({
    queryKey: candidateProfileKeys.activity(id ?? ""),
    queryFn: () => candidateService.listActivity(id as string),
    enabled: Boolean(id),
  })
}

function useInvalidateNotesAndActivity(id: string) {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: candidateProfileKeys.notes(id) })
    void queryClient.invalidateQueries({ queryKey: candidateProfileKeys.activity(id) })
  }
}

export function useCreateCandidateNote(id: string) {
  const invalidate = useInvalidateNotesAndActivity(id)
  return useMutation<CandidateNote, ApiError, { body: string; mentionedUserIds?: string[] }>({
    mutationFn: ({ body, mentionedUserIds }) => candidateService.createNote(id, body, mentionedUserIds),
    onSuccess: invalidate,
  })
}

export function useUpdateCandidateNote(id: string) {
  const invalidate = useInvalidateNotesAndActivity(id)
  return useMutation<
    CandidateNote,
    ApiError,
    { noteId: string; body: string; mentionedUserIds?: string[] }
  >({
    mutationFn: ({ noteId, body, mentionedUserIds }) =>
      candidateService.updateNote(id, noteId, body, mentionedUserIds),
    onSuccess: invalidate,
  })
}

export function useDeleteCandidateNote(id: string) {
  const invalidate = useInvalidateNotesAndActivity(id)
  return useMutation<void, ApiError, string>({
    mutationFn: (noteId) => candidateService.deleteNote(id, noteId),
    onSuccess: invalidate,
  })
}

export function usePinCandidateNote(id: string) {
  const queryClient = useQueryClient()
  return useMutation<CandidateNote, ApiError, { noteId: string; isPinned: boolean }>({
    mutationFn: ({ noteId, isPinned }) => candidateService.pinNote(id, noteId, isPinned),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: candidateProfileKeys.notes(id) })
    },
  })
}
