"""
CandidateNoteService — multi-author notes on a candidate's application,
distinct from ResumeFile.notes (the older single overwritable field still
used by the quick-actions "notes" dialog). Each note is attributed to its
author and only that author may edit or delete it.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.models.candidate_activity import ActivityEventType
from app.services.candidate_lookup import resolve_resume_file

if TYPE_CHECKING:
    from app.models.candidate_note import CandidateNote
    from app.models.user import User
    from app.repositories.campaign import CampaignRepository
    from app.repositories.candidate import CandidateRepository
    from app.repositories.candidate_activity import CandidateActivityRepository
    from app.repositories.candidate_note import CandidateNoteRepository
    from app.repositories.resume_file import ResumeFileRepository


class CandidateNoteService:
    def __init__(
        self,
        note_repo: CandidateNoteRepository,
        resume_file_repo: ResumeFileRepository,
        candidate_repo: CandidateRepository,
        campaign_repo: CampaignRepository,
        activity_repo: CandidateActivityRepository,
    ) -> None:
        self.note_repo = note_repo
        self.resume_file_repo = resume_file_repo
        self.candidate_repo = candidate_repo
        self.campaign_repo = campaign_repo
        self.activity_repo = activity_repo

    # ── Internal guards ──────────────────────────────────────────────────────

    def _require_org(self, user: User) -> uuid.UUID:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to manage candidate notes.",
            )
        return user.org_id

    async def _resolve_resume_file_id(self, id_: uuid.UUID, user: User) -> uuid.UUID:
        org_id = self._require_org(user)
        rf = await resolve_resume_file(
            id_, org_id, self.resume_file_repo, self.candidate_repo, self.campaign_repo
        )
        return rf.id

    async def _get_own_note(self, note_id: uuid.UUID, user: User) -> CandidateNote:
        note = await self.note_repo.get_by_id(note_id)
        if note is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found.")
        if note.author_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only edit or delete your own notes.",
            )
        return note

    # ── Public API ────────────────────────────────────────────────────────────

    async def list(self, id_: uuid.UUID, user: User) -> list[CandidateNote]:
        resume_file_id = await self._resolve_resume_file_id(id_, user)
        return await self.note_repo.list_by_resume_file(resume_file_id)

    async def create(
        self,
        id_: uuid.UUID,
        body: str,
        user: User,
        mentioned_user_ids: list[uuid.UUID] | None = None,
    ) -> CandidateNote:
        resume_file_id = await self._resolve_resume_file_id(id_, user)
        note = await self.note_repo.create(
            resume_file_id=resume_file_id,
            author_id=user.id,
            body=body,
            mentioned_user_ids=mentioned_user_ids or [],
        )
        await self.activity_repo.create(resume_file_id, user.id, ActivityEventType.NOTE_ADDED)
        return note

    async def update(
        self,
        id_: uuid.UUID,
        note_id: uuid.UUID,
        body: str,
        user: User,
        mentioned_user_ids: list[uuid.UUID] | None = None,
    ) -> CandidateNote:
        await self._resolve_resume_file_id(id_, user)
        note = await self._get_own_note(note_id, user)
        return await self.note_repo.update(
            note, body=body, mentioned_user_ids=mentioned_user_ids or []
        )

    async def delete(self, id_: uuid.UUID, note_id: uuid.UUID, user: User) -> None:
        await self._resolve_resume_file_id(id_, user)
        note = await self._get_own_note(note_id, user)
        await self.note_repo.delete(note)

    async def pin(
        self, id_: uuid.UUID, note_id: uuid.UUID, is_pinned: bool, user: User
    ) -> CandidateNote:
        """Pinning is a shared workspace affordance, not authorship — unlike
        edit/delete, any recruiter-role org member may pin/unpin any note."""
        await self._resolve_resume_file_id(id_, user)
        note = await self.note_repo.get_by_id(note_id)
        if note is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found.")
        return await self.note_repo.update(note, is_pinned=is_pinned)
