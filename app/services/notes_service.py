from app.models.note import Note
from uuid import UUID, uuid4
from sqlmodel.ext.asyncio.session import AsyncSession
from app.schemas.note import NoteCreate,NoteUpdate,NoteSearchResult
from sqlmodel import select 
from app.services.embeddings import encode_note,encode_query,encode_text,aencode_note,aencode_query

async def create_note(session:AsyncSession,note_in:NoteCreate)->Note:
    embedding=await aencode_note(title=note_in.title,content=note_in.content)
    db_note=Note(
        title=note_in.title,
        content=note_in.content,
        embedding=embedding
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

    
async def update_note(session:AsyncSession,id:UUID,updates:NoteUpdate)->Note:
    note=await get_note_by_id(session,id)
    if not note:
        raise ValueError("No note found")
    update_data = updates.model_dump(exclude_unset=True)
    new_title = update_data.get("title", note.title)
    new_content = update_data.get("content", note.content)
    if "title" in update_data or "content" in update_data:
        update_data["embedding"] = await aencode_note(title=new_title, content=new_content)
    note.sqlmodel_update(update_data)
    await session.commit()
    await session.refresh(note)
    return note


async def search_notes(session:AsyncSession,query:str,limit:int=5)->list[NoteSearchResult]:
    query_vector=await aencode_query(query)
    distance=Note.embedding.cosine_distance(query_vector)
    statement=(
        select(Note,distance).
        order_by(distance).
        limit(limit)
    )
    results=await session.exec(statement)
    search_results=[]
    for note,dist in results:
        note_dict=note.dump()
        search_results.append(
            NoteSearchResult(**note_dict, score=dist)
        )
        
    return search_results


async def delete_note(session:AsyncSession,id:UUID)->None:
    note=await get_note_by_id(session,id)
    if not note:
        raise ValueError("no note found")
    await session.delete(note)
    await session.commit()


# You don't await session.add(...) because add() is a synchronous method that only updates the in-memory unit‑of‑work / identity map — it does not do any I/O. The actual database work happens when you await session.flush() or await session.commit().