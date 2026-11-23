# One image for backend, worker-ai and worker-batch, always from the same commit (AD-24).
# Built from the repo root (`docker build -f backend/Dockerfile .`), as compose and Railway do.
FROM ghcr.io/astral-sh/uv:0.13.7 AS uv

FROM python:3.14-slim

COPY --from=uv /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Pango for WeasyPrint (AD-18): the chart print check (Story 6.7) and, later, the report PDFs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY backend/alembic.ini backend/docker-entrypoint.sh ./
COPY backend/migrations ./migrations
COPY backend/app ./app
RUN uv sync --locked --no-dev && chmod +x docker-entrypoint.sh

RUN useradd --system --uid 10001 app     && mkdir -p /app/.local-storage && chown app /app/.local-storage
# The storage mock's folder (Story 13.7): a named volume mounted here starts owned by `app`.
USER app

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
