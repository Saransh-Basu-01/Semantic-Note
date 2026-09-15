semantic-notes/
├── app/
│   ├── __init__.py
│   ├── main.py                 # create FastAPI app, include routers
│   ├── config.py               # all env vars from .env in one place
│   ├── db.py                   # engine + SessionLocal
│   ├── dependencies.py         # get_db dependency
│   ├── models/
│   │   ├── __init__.py
│   │   └── note.py             # only DB table definition
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── note.py             # Pydantic in/out schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── notes.py            # CRUD routes
│   │   └── search.py           # only /search route
│   └── services/
│       ├── __init__.py
│       ├── embeddings.py       # THE most important file - loads model once
│       └── notes_service.py    # business logic so routers stay thin
│
├── alembic/
│   ├── versions/
│   └── env.py
├── alembic.ini
│
├── scripts/
│   ├── seed.py                 # to fill 30-40 dummy notes for testing search
│   └── eval_search.py          # your golden queries to test if search works
│
├── tests/
│   ├── conftest.py
│   └── test_notes.py
│
├── ui/
│   └── app.py                  # Streamlit is perfect for this, fastest
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
├── .dockerignore
└── README.md