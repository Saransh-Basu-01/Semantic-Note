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