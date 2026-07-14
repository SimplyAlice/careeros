# CareerOS backend — single-stage image, appropriate for this project's
# scale. A multi-stage build (separate builder/runtime stages) is a
# documented option once the dependency set grows large enough that build
# tooling meaningfully bloats the final image — not needed yet.

FROM python:3.13-slim

# Prevents Python from writing .pyc files and buffering stdout/stderr —
# the latter matters so structured logs (see app/core/logging.py) appear
# immediately in `docker compose logs`, not batched.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System dependencies required by asyncpg / psycopg-style builds.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

# Run as a non-root user — a basic container security practice (see
# `docs/architecture/security.md`), not a stopgap for later.
RUN useradd --create-home --uid 1000 careeros \
    && chown -R careeros:careeros /app
USER careeros

EXPOSE 8000

# In docker-compose.yml this is overridden with --reload for local
# development; this default is the production-shaped command.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
