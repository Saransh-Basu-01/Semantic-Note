from typing import AsyncGenerator
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db import AsyncSessionLocal  

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session