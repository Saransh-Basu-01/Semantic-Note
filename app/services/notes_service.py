from app.models.note import Note
from uuid import UUID, uuid4
from sqlmodel.ext.asyncio.session import AsyncSession
from app.schemas.note import NoteCreate,NoteUpdate
from sqlmodel import select 

async def create_note(session:AsyncSession,note_in:NoteCreate)->Note:
    db_note=Note(
        title=note_in.title,
        content=note_in.content
    )
    session.add(db_note)
    await session.commit()
    await session.refresh(db_note)
    return db_note 
   

    
async def get_notes(session:AsyncSession,skip:int=0,limit:int=100)->list[Note]:
    statement = (
        select(Note)
        .order_by(Note.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await session.exec(statement)
    return list(result.all())


async def get_note_by_id(session:AsyncSession,id:UUID)->Note|None:
    result=await session.exec(select(Note).where(Note.id==id))
    note=result.first()
    return note

    
async def update_note(session:AsyncSession,id:UUID,updates:NoteUpdate):
    note=await get_note_by_id(session,id)
    if not note:
        raise ValueError("No note found")
    data=updates.model_dump(exclude_unset=True)
    note.sqlmodel_update(data)
    await session.commit()
    await session.refresh(note)
    return note



async def delete_note(session:AsyncSession,id:UUID)->None:
    note=await get_note_by_id(session,id)
    if not note:
        raise ValueError("no note found")
    await session.delete(note)
    await session.commit()


# You don't await session.add(...) because add() is a synchronous method that only updates the in-memory unit‑of‑work / identity map — it does not do any I/O. The actual database work happens when you await session.flush() or await session.commit().