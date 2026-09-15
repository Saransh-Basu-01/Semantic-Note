# Docker Compose Setup Explanation

This project uses a `docker-compose.yml` file to run the application stack locally with two services:

1. `db` → PostgreSQL database with pgvector extension
2. `api` → FastAPI backend application

It also defines persistent Docker volumes so data and model cache survive container restarts.

---

## High-level Architecture

- The **database service (`db`)** provides PostgreSQL + vector support.
- The **API service (`api`)** connects to `db` using an internal Docker network hostname (`db`).
- The API only starts after the database passes its health check.

---

## Service 1: `db` (PostgreSQL + pgvector)

```yaml
db:
  image: pgvector/pgvector:pg16
  env_file:
    - .env
  environment:
    POSTGRES_DB: ${POSTGRES_DB}
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  ports:
    - "5432:5432"
  volumes:
    - pgdata:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
    interval: 5s
    timeout: 5s
    retries: 5
```

### What each part does

- **`image: pgvector/pgvector:pg16`**  
  Uses a prebuilt PostgreSQL 16 image with the **pgvector** extension installed.  
  `pgvector` is useful for embedding/vector similarity use-cases.

- **`env_file: .env`**  
  Loads environment variables from your `.env` file into this service.

- **`environment:`**  
  Passes PostgreSQL startup variables:
  - `POSTGRES_DB` → database name to create
  - `POSTGRES_USER` → database username
  - `POSTGRES_PASSWORD` → password for that user

- **`ports: "5432:5432"`**  
  Maps container port 5432 to your local machine’s port 5432.  
  This lets tools on your host (psql, DBeaver, etc.) connect to DB.

- **`volumes: pgdata:/var/lib/postgresql/data`**  
  Persists database files in a named Docker volume (`pgdata`), so data is not lost when container restarts or is recreated.

- **`healthcheck`**  
  Runs `pg_isready` every 5 seconds to check DB readiness.
  - If DB is ready, health status becomes `healthy`.
  - If not ready after retries, it remains unhealthy.
  - Other services can depend on this health status.

---

## Service 2: `api` (FastAPI app)

```yaml
api:
  build: .
  ports:
    - "8000:8000"
  env_file:
    - .env
  environment:
    DATABASE_URL: "postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}"
    HF_HOME: /opt/hf_cache
  volumes:
    - .:/app
    - hf_cache:/opt/hf_cache
  command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  depends_on:
    db:
      condition: service_healthy
```

### What each part does

- **`build: .`**  
  Builds the API Docker image from the current directory (expects a `Dockerfile`).

- **`ports: "8000:8000"`**  
  Exposes FastAPI on port 8000 of your local machine.  
  You can access it at: `http://localhost:8000`.

- **`env_file: .env`**  
  Loads shared environment variables for the API service too.

- **`environment:`**
  - `DATABASE_URL`  
    SQLAlchemy/asyncpg DB connection string.  
    Important detail: host is `db` (the Docker service name), **not** `localhost`.
  - `HF_HOME: /opt/hf_cache`  
    Sets Hugging Face cache directory inside container.

- **`volumes:`**
  - `.:/app`  
    Mounts your project source code into container at `/app`.  
    Useful for development + live reload.
  - `hf_cache:/opt/hf_cache`  
    Keeps model/cache downloads persistent in Docker volume.

- **`command:`**
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  ```
  Starts FastAPI with Uvicorn:
  - `app.main:app` → Python module + ASGI app instance
  - `--host 0.0.0.0` → listens on all interfaces in container (required for port mapping)
  - `--port 8000` → serves on port 8000
  - `--reload` → auto-reload on code changes (dev mode)

- **`depends_on` with health condition**
  ```yaml
  depends_on:
    db:
      condition: service_healthy
  ```
  Ensures API starts only after DB healthcheck reports `healthy`.  
  This reduces startup race conditions (API trying DB before DB is ready).

---

## Volumes section

```yaml
volumes:
  pgdata:
  hf_cache:
```

Defines named volumes used by services:

- **`pgdata`** → PostgreSQL data persistence
- **`hf_cache`** → Hugging Face cache persistence

Named volumes are managed by Docker and survive container recreation unless explicitly removed.

---

## Why this setup is useful

- Clean separation of application and database
- Reproducible local environment for all developers
- Persistent DB and model cache
- Faster development with code mounting + `--reload`
- Safer service startup sequence via health checks

---

## Common mistakes to avoid

1. **YAML syntax errors**
   - Must use space after colon:
     - ✅ `HF_HOME: /opt/hf_cache`
     - ❌ `HF_HOME:/opt/hf_cache`

2. **Incorrect Uvicorn host flag**
   - ✅ `--host 0.0.0.0`
   - ❌ `-host 0.0.0.`

3. **Wrong DB host inside Docker**
   - Use service name `db`, not `localhost`, in `DATABASE_URL`.

---

## Run commands

```bash
docker compose up --build
```

To stop:

```bash
docker compose down
```

To stop and remove volumes too (deletes DB/cache data):

```bash
docker compose down -v
```