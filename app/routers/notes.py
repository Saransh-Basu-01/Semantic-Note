from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_session
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.notes_service import get_note_by_id,get_notes,delete_note,update_note,create_note
from app.schemas.note import NoteCreate,NoteRead,NoteUpdate
from typing import List
from uuid import UUID


router=APIRouter(prefix="/notes",tags=["noyes"])

@router.post(
    "/create",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    payload:NoteCreate,
    session:Annotated[AsyncSession,Depends(get_session)]
):
    note=await create_note(session=session,note_in=payload)
    return note


@router.get(
    "/notes",
    response_model=List[NoteRead]
)
async def read_notes(
    session:Annotated[AsyncSession,Depends(get_session)]
):
    notes=await get_notes(session=session)
    return notes


@router.get(
    "/notes/{note_id}",
    response_model=NoteRead
)
async def read_note(
    note_id:UUID,
    session:Annotated[AsyncSession,Depends(get_session)]
):
    note=await get_note_by_id(session=session,id=note_id)
    if not note:
        raise HTTPException(status_code=404,detail="note not founf")
    return note



@router.patch(
    "/notes/{note_id}",
    response_model=NoteRead
)
async def update(
    note_id:UUID,
    payload:NoteUpdate,
    session:Annotated[AsyncSession,Depends(get_session)]
):
    updates=await update_note(session,note_id,payload)
    return updates

@router.delete("/notes/{note_id}",status_code=204)
async def delete(
    note_id:UUID,
    session:Annotated[AsyncSession,Depends(get_session)]
):
    deleted=await delete_note(session=session,id=note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")
    return None
