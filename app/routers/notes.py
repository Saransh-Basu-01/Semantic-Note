from fastapi import APIRouter,Depends,status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_session
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.notes_service import get_note_by_id,get_notes,delete_note,update_note,create_note
from app.schemas.note import NoteCreate,NoteRead,NoteUpdate
from app.models.note import Note

router=APIRouter(prefix="/semantic",tags=["semantic"])

@router.post(
    "/create",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_notes(
    payload:NoteCreate,
    session:Annotated[AsyncSession,Depends(get_session)]
):
    note=await create_note(session=session,note_in=payload)
    return note


@router.get(
    "/get_notes"
    response_model=list[NoteRead]
)
async def get_notes(
    payload:NoteRead,
    session:Annotated[AsyncSession,Depends(get_session)]
):
    note=
    