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

LLM players' Orders are background jobs. Compose starts `worker-ai` (`python -m app.worker --queues ai-orders`) and `worker-batch` (`--queues llm-batch`) from the backend image; without Docker, run `cd backend && uv run python -m app.worker --queues ai-orders` in a third terminal. `worker-ai` also runs a rescue loop every 5 seconds: an LLM player still without an Order past its Effort level's time budget gets the Rule-based reference Order, marked `timeout`, and a complete Week left open is advanced. No key is needed: the AI mock answers locally.

Checking the real LLM endpoint (OpenRouter) by hand needs the key in your environment; tests and CI never call it. With the compose `postgres` running:

```sh
cd backend
export OPENROUTER_API_KEY=...   # never commit or paste it into a config file
uv run python -m app.ai.cli config add ai-configs/openrouter-deepseek.json      # prints: config <ID>
uv run python -m app.ai.cli budget set --evaluation <ID> --limit 1 --reserve 0
uv run python -m app.sim endpoint --config <ID>     # model id, 3 Orders, a burst of 5, latency, cost
```

### Measuring a model and Effort level (Story 2.11)

`python -m app.sim run <batch>` stores the batch (its file, pass lines and whether the mock answered) and prints `batch_id <id>`; `python -m app.sim report <id>` prints per Game and for the batch the AI cost, tokens, latency per attempt, time per Order (median, p95), retries, fallback share by type, Play guard switches, the Share of LLM Orders, the variation of chain Total cost, whether the cost limit cut the batch short, and pass or miss against the batch file's pass lines. A batch the mock answered says so on its first line. CI runs `backend/scripts/sim-llm-smoke.sh` (mock config, `worker-ai`, report).

The real measurement (OpenRouter, `deepseek/deepseek-v4.1-flash-1017`, issue #9) needs the key in your environment and is run by hand. With the compose `postgres` running and migrated:

```sh
cd backend
export OPENROUTER_API_KEY=...   # never commit or paste it into a config file
uv run python -m app.ai.cli config add ai-configs/openrouter-deepseek.json      # prints: config <ID>
uv run python -m app.ai.cli budget set --evaluation <ID> --limit 1 --reserve 0  # hard cap: USD 1
uv run python -m app.sim run batches/measure-openrouter-small.json --config <ID>  # prints: batch_id <B>
uv run python -m app.sim report <B>
```

`measure-openrouter-small.json` plays 2 Classic Games (it has no `settings`, so 36 Weeks with 4 Guided) with 4 LLM Seats: 256 LLM Orders, about 10 to 15 minutes at the config's 60 requests per minute. Its pass lines are USD 0.10 per Game (C-3), 8 s p95 per Order (NFR-2, placeholder) and at most 25 % of LLM Seats switched (placeholder, issue #20). Change `games` for a larger batch. Estimate at the config's placeholder prices (USD 0.12 / 0.48 per million input / output tokens), with about 1,000 input and 150 to 800 output tokens per attempt (the request is 2.5 to 3.8 kB of JSON on Classic), no retries:

| Games | LLM Orders | Expected cost (USD) | Reserved worst case (USD) |
|------:|-----------:|--------------------:|--------------------------:|
| 1 | 128 | 0.03 – 0.06 | 0.31 |
| 2 (default) | 256 | 0.06 – 0.12 | 0.63 |
| 5 | 640 | 0.15 – 0.30 | 1.57 |
| 10 | 1,280 | 0.30 – 0.60 | 3.14 |
| 20 | 2,560 | 0.60 – 1.20 | 6.28 |

The worst case is what the gateway reserves per attempt (request size plus the Effort level's 4,096 `max_output_tokens`); retries add up to 5 more attempts per Order. Set the budget limit at or above the expected cost (`--limit 1` covers the default batch; raise it for 10 Games or more): when it runs out, the rest of the batch is played by Rule-based players and the report marks the batch as cut short and misses every pass line.

### Offering an Effort level and pinning the model (Story 2.12)

A batch that ran on the real endpoint and passed its cost, time and switched-share lines becomes the measurement of its Effort level; the default model config is the one pinned last:

```sh
uv run python -m app.sim approve <B> --level standard   # prints the report, then: approved config <ID> …
uv run python -m app.ai.cli pin <ID>                     # the default for new Class sessions, with its evidence
uv run python -m app.ai.cli config show <ID>             # the config, its offered levels and measurements, active_default
```

`approve` is refused when the mock answered the batch (`mock_batch`), when a line is missing or missed (a cut-short batch misses every line), when the batch played another level, or when it was approved before. Only approved levels whose endpoint can be reached here are offered (`ai.config.offered_effort_levels`, read by Epic 5); `pin` is refused for a config with none. A Class session or Game keeps the config id it was created with when the default changes later.

Zero config: in `local`, `test` and `ci`, when no model config is stored, the api, the workers and `python -m app.sim` seed a config named `mock` (the content of `ai-configs/mock.json`) with a measurement marked `mock`, a USD 10 evaluation budget of mock money, and pin it. Mock measurements count only there: with `APP_ENV=production` nothing is seeded, a mock batch is never approved, the mock config is never pinned, and a database with only mock measurements offers no Effort level at all. A local database that already held configs before Story 2.12 is not seeded; pin one with `uv run python -m app.ai.cli pin <ID>` once it offers a level. The active default is the newest pin whose config offers a level here.

Every LLM attempt first reserves its worst-case cost (request size and the Effort level's `max_output_tokens` at the config's prices) on the scope's budget row; LLM players may spend only `limit − reserve`. When a player's reservation does not fit, every LLM Seat of every running Game on that budget switches to a Rule-based player for good. `uv run python -m app.ai.cli cost --scope <ID>` prints the budget row and the AI cost per Game and per day.

### How the AI players decide (Story 2.13)

`uv run python -m app.sim describe` prints the Norwegian description of the Rule-based player and of the LLM player, each after a `description <kind> v<N>` line; it uses no database. The texts live in `backend/app/modules/players/descriptions/v<N>/` and are read with `players.service.describe(kind)`. A shipped text is never edited (a test pins its hash): a change is a new version folder. Tests tie the texts to the code: the Rule-based text may name only the inputs the rule reads, and must say its parameters are unverified while the placeholder set is the default. The LLM text's claims about what the model sees are checked against the Story 2.4 prompt checks. Its fallback cases are checked against the gateway's failure kinds, and its Play guard sentences against the guard's parameter set; the switch behaviour itself is tested in Stories 2.5, 2.8 and 2.10.

`openrouter-deepseek.json` goes through OpenRouter's global router (`openrouter.ai`) to one upstream endpoint run by an EU company (Nebius, zero retention, no fallback); the router itself is not EU-only. `ai-configs/openrouter-deepseek-eu.json` uses OpenRouter's EU in-region endpoint (`eu.openrouter.ai`, Business plan), which keeps prompts in the EU. The region, upstream provider, routing switches, prices and rate limit are config data.

### Logging in locally (Story 3.2)

With `APP_ENV=local` (the compose default) and an empty `users` table, the backend seeds two demo accounts at start. Nothing is seeded in any other environment.

| Role | E-post | Passord |
|------|--------|---------|
| Admin | `admin@example.com` | `olspillet-demo` |
| Faglærer (Lecturer) | `faglaerer@example.com` | `olspillet-demo` |

Log in at <http://127.0.0.1:8080/logg-inn>. A database that already holds Users is not seeded again. To start over, empty the tables with `docker compose exec postgres psql -U olspillet -c "TRUNCATE users CASCADE"`, then restart `backend`.

Playwright tests and visual checks use the same test login: `frontend/e2e/support/auth.ts` exports `DEMO_USERS`, `DEMO_PASSWORD`, `loginAs(page, role)` (through the «Logg inn» page) and `loginByApi(page, role)` (through the API only, which is faster). `role` is `admin` or `lecturer`.

Session and login:

- The session is an HS256 JWT in the `olspillet_session` cookie (`HttpOnly; Secure; SameSite=Lax`). Chromium and Firefox keep a `Secure` cookie on `http://127.0.0.1` and `http://localhost`; Safari may not, so log in locally with Chromium or Firefox. `JWT_SECRET` has a local default and must be set to a long random value outside local (the production guard comes with Story 3.14). `SESSION_MAX_AGE_HOURS` defaults to 168. Logout deletes the cookie; a copied token stays valid until it expires unless the User is deactivated.
- Every mutating `/api` request needs the header `X-Requested-With: olspillet`. The generated client sends it.
- Failed logins are rate-limited in Postgres. The limits are placeholders until the pilot: `LOGIN_RATE_LIMIT_PER_IP` (300), `LOGIN_RATE_LIMIT_PER_ACCOUNT` (5) and `LOGIN_RATE_LIMIT_WINDOW_MINUTES` (15). A successful login resets the account's count.
- `BCRYPT_ROUNDS` (12) sets the hashing cost. The tests use 4.

The typed API client in `frontend/src/lib/api/` is generated from the backend's OpenAPI schema. After you change a route or schema, regenerate it:

```sh
cd backend && uv run python -m app.openapi ../frontend/src/lib/api/openapi.json
cd frontend && npm run api:generate
```

CI regenerates both files and fails on any difference.

Checks, as CI runs them:

```sh
cd backend && uv sync --locked && uv run ruff check . && uv run ruff format --check . && uv run pytest
cd frontend && npm ci && npm run typecheck && npm test && npm run check:copy && npm run build
docker compose up -d --build --wait proxy && (cd frontend && npx playwright test)
```

`uv run pytest` needs the compose `postgres` (or `DATABASE_URL`) and uses a separate `<db>_test` database.

Frontend checks:

- `npm test` runs Vitest. It covers the theme tokens against `DESIGN.md`, the text-on-tint contrast pairs, the components, the copy check and the colour lint.
- `npm run check:copy` runs the voice rules over `src/copy/nb.ts`, the print route and the Jinja2 templates.
- `npm run build` runs the colour lint first. It fails on a literal colour outside `src/theme/`.
- `npx playwright test` runs the browser tests, with axe, against the stack at `http://127.0.0.1:8080`. Use 127.0.0.1, not `localhost`. Set `E2E_BASE_URL` to point them at another address. Install the browser once with `npx playwright install chromium`.
- The theme is generated from `src/theme/tokens.json`, which is a copy of the `DESIGN.md` front matter. After a token change, run `npm run theme`.

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
