# semantic-notes

A small FastAPI project for storing notes and performing semantic search using embeddings. This README documents the project layout, purpose of each file/folder, and quick-start instructions for development and testing.

## Table of contents
- Project structure
- File & folder descriptions
- Quick start
- Running tests
- Development notes
- Contributing

## Project structure

semantic-notes/
├── app/  
│   ├── __init__.py  
│   ├── main.py                 # Create FastAPI app, include routers and middleware  
│   ├── config.py               # Centralized environment/config parsing (from .env)  
│   ├── db.py                   # SQLAlchemy engine, Base, and SessionLocal factory  
│   ├── dependencies.py         # FastAPI dependency functions (e.g., get_db)  
│   ├── models/  
│   │   ├── __init__.py  
│   │   └── note.py             # SQLAlchemy model for notes table  
│   ├── schemas/  
│   │   ├── __init__.py  
│   │   └── note.py             # Pydantic models for request/response (NoteCreate, NoteRead, NoteUpdate)  
│   ├── routers/  
│   │   ├── __init__.py  
│   │   ├── notes.py            # CRUD endpoints for notes (GET, POST, PUT, DELETE)  
│   │   └── search.py           # /search endpoint that uses embeddings + vector search  
│   └── services/  
│       ├── __init__.py  
│       ├── embeddings.py       # Loads embedding model once (singleton/module-level) and exposes vectorize functions  
│       └── notes_service.py    # Business logic: create/read/update/delete/search (keeps routers thin)  
│
├── alembic/  
│   ├── versions/               # Generated migration scripts  
│   └── env.py                  # Alembic environment config  
├── alembic.ini                 # Alembic configuration file  
│
├── scripts/  
│   ├── seed.py                 # Populate DB with sample notes for development/testing search quality  
│   └── eval_search.py          # Golden queries / validation scripts for search results  
│
├── tests/  
│   ├── conftest.py             # pytest fixtures (test DB, test client, etc.)  
│   └── test_notes.py           # Unit/integration tests for notes endpoints and search  
│
├── ui/  
│   └── app.py                  # Streamlit app for quick UI / prototyping the search experience  
│
├── docker-compose.yml  
├── Dockerfile  
├── requirements.txt  
├── .env.example  
├── .gitignore  
├── .dockerignore  
└── README.md

## File & folder descriptions

- app/main.py
  - Create, configure, and mount the FastAPI application. Register routers and middleware here.

- app/config.py
  - Load and validate environment variables, central place for configuration values (DB URL, model paths, API keys, etc).

- app/db.py
  - SQLAlchemy engine setup, Base model import, and SessionLocal factory to produce DB sessions.

- app/dependencies.py
  - FastAPI dependencies (e.g., get_db that yields a DB session and closes it after use).

- app/models/note.py
  - SQLAlchemy model defining the notes table (id, title, content, embedding vector reference/id/tokens, timestamps).

- app/schemas/note.py
  - Pydantic schemas used for request/response validation (NoteCreate, NoteRead, NoteUpdate).

- app/routers/notes.py
  - RESTful CRUD endpoints for managing notes.

- app/routers/search.py
  - Endpoint(s) for semantic search; delegates to services/embeddings.py and services/notes_service.py.

- app/services/embeddings.py
  - Load embedding model once at module import (or using an async-safe singleton). Expose vectorize(text) and batch vectorize utilities.

- app/services/notes_service.py
  - Business logic to handle note creation (store embeddings), search (vector retrieval + ranking), and other domain logic.

- alembic/
  - Database migration scripts and Alembic config for versioned schema changes.

- scripts/seed.py
  - Create 30–40 sample notes to exercise and evaluate search.

- scripts/eval_search.py
  - Scripts with golden queries & expected behavior to validate search quality after changes.

- tests/
  - Test suite and fixtures to validate endpoints and search behavior.

- ui/
  - Small Streamlit or simple web UI to interact with the API and test search.

- Docker / deployment
  - Dockerfile + docker-compose.yml for local development and composing dependent services (Postgres / Redis / vector DB).

## Quick start (development)

1. Install dependencies
   - Create a virtual environment and install:
     - pip install -r requirements.txt

2. Environment
   - Copy `.env.example` to `.env` and adjust values (DATABASE_URL, EMBEDDING_MODEL, API keys, etc).

3. Database
   - Start Postgres (or use docker-compose).
   - Run Alembic migrations:
     - alembic upgrade head

4. Seed data (optional but recommended)
   - python scripts/seed.py

5. Run the app
   - uvicorn app.main:app --reload

6. UI (optional)
   - cd ui && streamlit run app.py

## Running tests

- Use pytest:
  - pytest -q

- Tests rely on fixtures in tests/conftest.py that create an isolated test DB and test client.

## Development notes

- Keep embedding model loading centralized in services/embeddings.py so the model loads only once per process.
- Persist embeddings alongside notes (or store vector IDs if using an external vector DB) to avoid recomputing on every search.
- Encapsulate search ranking and similarity logic in notes_service.py so routers stay thin and testable.
- Add golden queries to scripts/eval_search.py for continuous regression checks on search quality.

## Contributing

- Follow the existing style and add tests for new behavior.
- Open an issue describing the change or a PR with a clear description and tests.
- Use Alembic for DB schema changes and include migration files in `alembic/versions`.

## License

- Add a LICENSE file at the repo root if you intend to open-source this project.
