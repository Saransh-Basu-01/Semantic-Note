import asyncio
import sys
from pathlib import Path

# make sure app is importable
sys.path.append(str(Path(__file__).parent.parent))

from sqlmodel import delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.note import Note
from app.config import settings
from app.services.embeddings import encode_note  # sync version is fine for seeding

NOTES = [
    {"title": "Passport renewal process in Nepal", "content": "To renew Nepali passport, go to Department of Passports in Babarmahal with old passport, citizenship, and online form. Takes 2-3 days for normal processing."},
    {"title": "Best momos in Kathmandu", "content": "Try authentic buff momos at Newa Mo:Mo in Jhamsikhel, and chicken jhol momos at Le Sherpa. Bota and Narayan Dai are legendary for local taste."},
    {"title": "Docker setup for Postgres with pgvector", "content": "Use image pgvector/pgvector:pg16. Mount volume for data, enable extension CREATE EXTENSION vector. Port 5432 to host."},
    {"title": "How to create HNSW index in pgvector", "content": "CREATE INDEX ON notes USING hnsw (embedding vector_cosine_ops). HNSW is faster than IVFFLAT for large datasets and supports cosine similarity."},
    {"title": "FastAPI dependency injection", "content": "Use Depends() to inject DB sessions, current user, and settings. Keeps routers thin and testable by separating concerns."},
    {"title": "Everest Base Camp trek checklist", "content": "Need down jacket, trekking boots, Diamox for altitude, TIMS card, Sagarmatha permit. Best seasons are March-May and Sept-Nov."},
    {"title": "Chicken curry recipe", "content": "Marinate chicken with yogurt, turmeric, chili. Fry onions, tomatoes, ginger garlic, add garam masala and slow cook for 30 minutes."},
    {"title": "What are embeddings in ML", "content": "Embeddings convert text into dense vectors in high dimensional space where similar meaning texts are close together. Used for semantic search."},
    {"title": "Fixing Alembic migration errors", "content": "If revision fails, check env.py imports your SQLModel metadata and models. Delete versions folder if stuck in dev and recreate."},
    {"title": "Pashupatinath Temple guide", "content": "Sacred Hindu temple on Bagmati river. Non-Hindus cannot enter main temple but can view from other side. Evening aarati at 6pm is beautiful."},
    {"title": "SQLModel vs SQLAlchemy", "content": "SQLModel combines Pydantic and SQLAlchemy. Good for FastAPI because same model can be DB table and request/response schema."},
    {"title": "Deploy FastAPI on Render", "content": "Create Dockerfile, set start command uvicorn app.main:app --host 0.0.0.0 --port $PORT. Add DATABASE_URL from external postgres."},
    {"title": "Perfect filter coffee at home", "content": "Use 70% coffee 30% chicory, 1:10 ratio with hot water in South Indian filter. Let decoction drip slowly for 20 minutes."},
    {"title": "PyTorch for beginners", "content": "Tensors are like numpy arrays with GPU support. Start with torch.tensor, autograd for automatic differentiation, and DataLoader for training."},
    {"title": "Dashain festival traditions", "content": "Biggest festival in Nepal. 15 days, tika from elders, flying kites, playing cards, and family gatherings. Celebrates victory of good over evil."},
    {"title": "How to write a good README", "content": "Include project title, demo gif, setup instructions, env variables, API docs, and license. Keep it short but cover how to run locally."},
    {"title": "Cosine similarity vs dot product", "content": "Cosine measures angle between vectors ignoring magnitude, good for normalized embeddings. Dot product considers both angle and magnitude."},
    {"title": "Budget travel tips for Pokhara", "content": "Stay in Lakeside hostels, rent scooter for 800 NPR per day, visit Phewa Lake, Sarangkot sunrise, and eat at local thakali places."},
    {"title": "JWT authentication in FastAPI", "content": "Use python-jose to create access tokens, store secret in .env, add OAuth2PasswordBearer dependency to protect routes."},
    {"title": "Indoor gardening in Kathmandu valley", "content": "Money plant, snake plant, and aloe vera grow well in low light. Water twice a week in winter, keep near window for indirect sunlight."},
]

async def seed():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("Clearing old notes...")
        await session.exec(delete(Note))
        await session.commit()

        print(f"Seeding {len(NOTES)} notes with embeddings (first run will download model)...")
        for i, item in enumerate(NOTES, 1):
            print(f"[{i}/{len(NOTES)}] {item['title']}")
            embedding = encode_note(item["title"], item["content"])
            note = Note(title=item["title"], content=item["content"], embedding=embedding)
            session.add(note)
        
        await session.commit()
        print("Done! All notes seeded with 384-dim vectors.")

if __name__ == "__main__":
    asyncio.run(seed())