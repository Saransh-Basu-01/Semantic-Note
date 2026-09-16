from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index
from sqlmodel import SQLModel, Field, Column
from pgvector.sqlalchemy import Vector


class NoteBase(SQLModel):
    title: str
    content: str


class Note(NoteBase, table=True):
    __tablename__ = "notes"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # 384 dims — all-MiniLM-L6-v2
    embedding: Optional[List[float]] = Field(
        default=None,
        sa_column=Column(Vector(384)),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),          
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)}, 
    )

    __table_args__ = (
        Index(
            "ix_notes_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

# SQLModel is an open-source Python library designed to act as a bridge between your SQL database and your FastAPI application