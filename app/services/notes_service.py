from app.models.note import Note
from datetime import datetime, timedelta, timezone
from app.config import settings
from sqlalchemy.exc import IntegrityError

from sqlmodel.ext.asyncio.session import AsyncSession
from app.schemas.note import NoteCreate,NoteRead,NoteUpdate


async def create_note(session:AsyncSession,note_in:NoteCreate)->Note:
    db_note=Note(
        title=note_in.title,
        content=note_in.content
    )
    try:
        session.add(db_note)
        await session.commit()
        await session.refresh(db_note)
        return db_note 
    except IntegrityError as e:
        session.rollback()
        raise ValueError("Database error while creating product") from e

    
async def get_notes(session:AsyncSession,skip:int=0,limit:int=100):
    notes=session.query(Note).offset(skip).limit(limit).all()
    return notes


async def get_note_by_id(session:AsyncSession,id:int)->Note|None:
    note=session.query(Note).filter(Note.id==id).first()
    return note

    
async def update_note(session:AsyncSession,id:int,updates:NoteUpdate):
    note=get_note_by_id(session,id)
    if not Note:
        raise ValueError("No note found")



async def delete_note(session:AsyncSession,id:int):
    note=get_note_by_id(session,id)
    if not note:
        raise ValueError("no note found")
    try:
        session.delete(note)
        session.commit()
        return True
    except IntegrityError as e:
        session.rollback()
        raise ValueError("Cannot delete product due to foreign key constraints") from e