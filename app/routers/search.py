from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.note import NoteSearchResult


router=APIRouter(prefix="/search",tags=["search"])
@router.get(
    "/search",
    response_model=list[NoteSearchResult]
)
async def search(query:str,limit:int=5)->NoteSearchResult:
    

