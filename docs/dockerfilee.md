# Dockerfile Detailed Explanation (FastAPI + `uv` + Python 3.12)

This Dockerfile builds a production-style Python container for a FastAPI app, using:

- `python:3.12-slim` as the base image
- `uv` (Astral’s fast Python package manager) for dependency sync
- a virtual environment located at `/opt/venv`
- `uvicorn` as the ASGI server

---

## Full Dockerfile

```dockerfile
# ---------- base ----------
FROM python:3.12-slim

# unbuffered = logs show up immediately in docker logs
# bytecode compiled at build = faster startup
# venv lives OUTSIDE /app (critical — see note 1)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

# grab the uv binary from the official image — no pip needed
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# dependencies first — this layer is cached until pyproject/lock change
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# app code last — it changes most often, so keep it in the cheapest layer
COPY . .

# make venv binaries (uvicorn, python) directly callable
ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Line-by-line explanation

---

### 1) Base image

```dockerfile
FROM python:3.12-slim
```

- Uses official Python 3.12 image.
- `slim` variant reduces image size compared to full Debian-based image.
- Good default for API apps where you want smaller deploy artifacts.

---

### 2) Environment variables

```dockerfile
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv
```

#### `PYTHONUNBUFFERED=1`
- Disables output buffering for Python stdout/stderr.
- Logs appear immediately in `docker logs` (important for debugging in containers).

#### `PYTHONDONTWRITEBYTECODE=1`
- Prevents creation of `.pyc` bytecode files.
- Keeps container filesystem cleaner.
- Avoids unnecessary writes in ephemeral environments.

#### `UV_PROJECT_ENVIRONMENT=/opt/venv`
- Tells `uv` to create/manage the virtual environment at `/opt/venv`.
- This keeps the venv outside `/app`, which is useful when `/app` may be bind-mounted during development.
- Helps avoid virtualenv being overwritten by host mount.

---

### 3) Copy `uv` binary from official image

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
```

- Multi-stage style copy from `ghcr.io/astral-sh/uv:latest`.
- Pulls `uv` and `uvx` executables directly; no `pip install uv` required.
- Benefits:
  - faster build
  - cleaner dependency management
  - avoids bootstrapping package manager with package manager

---

### 4) Set working directory

```dockerfile
WORKDIR /app
```

- All following commands run in `/app`.
- This is where project files are copied and app runs from.

---

### 5) Copy dependency metadata first

```dockerfile
COPY pyproject.toml uv.lock ./
```

- Copies only dependency definition files initially.
- Enables Docker layer caching:
  - If app code changes but dependencies don’t, Docker can reuse dependency install layer.
- Speeds up rebuilds significantly.

---

### 6) Install/sync dependencies with cache mount

```dockerfile
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project
```

This is the most important build step.

#### `--mount=type=cache,target=/root/.cache/uv`
- BuildKit cache mount for downloaded packages and metadata.
- Makes repeated builds faster by reusing package cache.
- Requires Docker BuildKit (enabled by default in modern Docker).

#### `uv sync`
- Creates/syncs environment from lockfile.

#### `--frozen`
- Enforces lockfile correctness.
- Build fails if lockfile and project metadata are inconsistent.
- Great for reproducible builds.

#### `--no-install-project`
- Installs dependencies only, not your local project package itself.
- Useful when app source is copied later.
- Keeps dependency layer stable and cache-friendly.

---

### 7) Copy application code

```dockerfile
COPY . .
```

- Copies full project into `/app`.
- Done after dependency install to maximize cache reuse.
- Since code changes frequently, this should be in later layers.

---

### 8) Put virtualenv binaries in PATH

```dockerfile
ENV PATH="/opt/venv/bin:$PATH"
```

- Makes tools inside venv directly executable:
  - `python`
  - `uvicorn`
  - installed CLI scripts
- Avoids writing full path like `/opt/venv/bin/uvicorn`.

---

### 9) Expose service port

```dockerfile
EXPOSE 8000
```

- Documents that container listens on port `8000`.
- Does not publish port by itself (port mapping happens in Docker Compose or `docker run -p`).

---

### 10) Default startup command

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- Starts FastAPI with Uvicorn.
- `app.main:app` means:
  - module: `app.main`
  - ASGI object: `app`
- `--host 0.0.0.0` allows connections from outside container.
- `--port 8000` runs server on port 8000.

---

## Why this Dockerfile structure is good

1. **Small runtime image** (`python:3.12-slim`)
2. **Fast rebuilds** (dependency layering)
3. **Reproducibility** (`uv.lock` + `--frozen`)
4. **Clear runtime behavior** (explicit CMD)
5. **Container-friendly logging** (`PYTHONUNBUFFERED=1`)

---

## Build and run examples

### Build image
```bash
docker build -t my-fastapi-app .
```

### Run container
```bash
docker run --rm -p 8000:8000 my-fastapi-app
```

Then open:
- `http://localhost:8000`
- `http://localhost:8000/docs` (if FastAPI docs enabled)

---

## Common gotchas

1. **`uv.lock` missing**
   - `uv sync --frozen` may fail if lock file is absent or outdated.
   - Regenerate lock locally, then rebuild.

2. **BuildKit not enabled**
   - Cache mount syntax may fail on old Docker setups.
   - Enable BuildKit if needed.

3. **Wrong app import path**
   - If your app object is not `app.main:app`, update CMD accordingly.

4. **Port not accessible**
   - Need host mapping (`-p 8000:8000`) in `docker run`, or equivalent in Compose.

---

## Optional improvements (if you want later)

- Add a non-root user for better security.
- Add healthcheck endpoint and Docker `HEALTHCHECK`.
- Use multi-stage final runtime image with only needed files.
- Add `--reload` only for development profile (not production).