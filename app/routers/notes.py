from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_session
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.notes_service import get_note_by_id, get_notes, delete_note, update_note, create_note
from app.schemas.note import NoteCreate, NoteRead, NoteUpdate
from typing import List
from uuid import UUID

router = APIRouter(prefix="/notes", tags=["notes"])

# CREATE - POST /notes
@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
async def create(
    payload: NoteCreate,
    session: Annotated[AsyncSession, Depends(get_session)]
):
    note = await create_note(session=session, note_in=payload)
    return note

# LIST - GET /notes
@router.get("", response_model=List[NoteRead])
async def list_all(
    session: Annotated[AsyncSession, Depends(get_session)],
    skip: int = 0,
    limit: int = 100
):
    notes = await get_notes(session=session, skip=skip, limit=limit)
    return notes

# READ ONE - GET /notes/{id}
@router.get("/{note_id}", response_model=NoteRead)
async def get_one(
    note_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)]
):
    note = await get_note_by_id(session=session, id=note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

# UPDATE - PATCH /notes/{id}
@router.patch("/{note_id}", response_model=NoteRead)
async def update_one(
    note_id: UUID,
    payload: NoteUpdate,
    session: Annotated[AsyncSession, Depends(get_session)]
):
    note = await get_note_by_id(session=session, id=note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    updated = await update_note(session, note_id, payload)
    return updated

# DELETE - DELETE /notes/{id}
@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_one(
    note_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    note = await get_note_by_id(session=session, id=note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    await delete_note(session=session, id=note_id)
    return None