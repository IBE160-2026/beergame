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

LLM players' Orders are background jobs. Compose starts `worker-ai` (`python -m app.worker --queues ai-orders`) and `worker-batch` (`--queues llm-batch`) from the backend image; without Docker, run `cd backend && uv run python -m app.worker --queues ai-orders` in a third terminal. No key is needed: the AI mock answers locally.

Checks, as CI runs them:

```sh
cd backend && uv sync --locked && uv run ruff check . && uv run ruff format --check . && uv run pytest
cd frontend && npm ci && npm run typecheck && npm run build
```

`uv run pytest` needs the compose `postgres` (or `DATABASE_URL`) and uses a separate `<db>_test` database.

## Fast tests

`uv run pytest` is the full suite CI runs, spread over up to 12 workers (pytest-xdist); each worker gets its own `<db>_test_gw<N>` database. It takes about 40 s locally.

While working on one thing, run one file or one test in a single process:

```sh
cd backend && uv run pytest -n0 tests/games/test_start.py
cd backend && uv run pytest -n0 tests/games/test_start.py -k reference_order
```

New tests must stay fast:

- Use a short Game (`weeks=8`) unless the 36 Weeks are what the test checks.
- Do not play the same Game twice: tests that only read a played Game take a copy with `classic_game` or `played_once` in `tests/games/helpers.py`.
- No fixed waits: read events with `listening(...).drain()`, which returns as soon as they have arrived.
- Use a batch of one or two Games unless the batch size is the point.
- Check `uv run pytest --durations=20` before you commit; a test over a few seconds needs a reason.
