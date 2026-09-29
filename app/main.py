from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.notes import router as notes_router
from app.routers.search import router as search_router
app = FastAPI(
    title="Semantic Notes API",
    description="A lightweight semantic note-taking API powered by FastAPI, SQLModel, and pgvector",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Register your notes router
app.include_router(notes_router)
app.include_router(search_router)

@app.get("/")
async def root():
    return {"message": "Semantic Notes API is running!"}