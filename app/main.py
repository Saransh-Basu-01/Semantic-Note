from fastapi import FastAPI
from app.routers.notes import router as notes_router

app = FastAPI(
    title="Semantic Notes API",
    description="A lightweight semantic note-taking API powered by FastAPI, SQLModel, and pgvector",
    version="0.1.0",
)

# Register your notes router
app.include_router(notes_router)


@app.get("/")
async def root():
    return {"message": "Semantic Notes API is running!"}