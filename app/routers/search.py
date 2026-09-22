from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.dependencies import get_session
from app.schemas.note import NoteSearchResult
from app.services.notes_service import search_notes

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/", response_model=list[NoteSearchResult])
async def search(
    query: str = Query(..., min_length=1, description="Search query string"),
    limit: int = Query(default=2, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> list[NoteSearchResult]:
    return await search_notes(session=session, query=query, limit=limit)