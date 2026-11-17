Dette er Beergame applikasjonen!

The code lives in two folders: `backend/` (FastAPI, Python) and `frontend/` (Next.js).

## Run locally

Needs Docker. No keys and no `.env` file: every variable has a default and every integration runs as a mock.

```sh
docker compose up --build
```

Then open <http://localhost:8080>. `GET /api/health` answers `200 {"status":"ok"}` once the backend has reached the database. Set `HTTP_PORT` or `POSTGRES_PORT` if 8080 or 5432 is taken.

Without Docker for the app itself: start Postgres with `docker compose up -d postgres`, then run the backend and frontend in two terminals. The backend reads environment variables, not `.env`.

```sh
cd backend && uv sync && uv run alembic upgrade head && uv run uvicorn app.main:app --reload
cd frontend && npm ci && npm run dev
```

Checks, as CI runs them:

```sh
cd backend && uv sync --locked && uv run ruff check . && uv run ruff format --check . && uv run pytest
cd frontend && npm ci && npm run typecheck && npm run build
```

`uv run pytest` needs the compose `postgres` (or `DATABASE_URL`) and uses a separate `<db>_test` database.
