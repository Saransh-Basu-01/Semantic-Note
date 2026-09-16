from pydantic import BaseModel,ConfigDict
from datetime import datetime
class NoteBase(BaseModel):
    title:str
    content:str

class NoteCreate(NoteBase):
    pass

class NoteUpdate(BaseModel):
    title:str|None=None
    content:str|None=None

class NoteRead(NoteBase):
    id:int
    created_at:datetime
    updated_at:datetime
    # Enables automatic mapping from SQLModel ORM objects to Pydantic responses
    model_config = ConfigDict(from_attributes=True)


# In Python, writing class NoteUpdate(): defines a standard Python class, not a Pydantic model. Pydantic will ignore it completely during FastAPI validation.

# Fix: Inherit from BaseModel: class NoteUpdate(BaseModel):

# (Added model_config = ConfigDict(from_attributes=True) to NoteRead so FastAPI can seamlessly convert your SQLModel database objects straight into JSON responses).