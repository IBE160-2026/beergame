---
title: 'Setup guide: ØL-spillet v1'
companion-of: ARCHITECTURE-SPINE.md
status: final
created: '2026-11-12'
updated: '2026-11-12'
---

# Setup guide: ØL-spillet v1

This guide covers how to create the accounts, services and keys that the architecture spine assumes, from a laptop to production. It is `technology.md` adapted to this project's MVP. The spine is authoritative: where this guide and the spine differ, the spine wins, and the AD numbers below point to it. **No secrets belong in this file or in git.** Only variable names appear here.

Legend: 🔴 secret (never in git, never with `NEXT_PUBLIC_`) · 🟡 non-secret config · ⚪ optional (mock without it) · 🟢 required in production.

---

## 1. What runs where

| Service | Railway service | Start command | Public? | Notes |
| --- | --- | --- | --- | --- |
| `proxy` | Caddy 2.11 | `caddy run --config /etc/caddy/Caddyfile` | yes, the only one | `/api/*` goes to `api` (immediate flush for SSE), everything else to `web` (AD-11). Plain HTTP behind Railway's TLS. |
| `web` | Next.js 16 standalone (Node 24) | `node server.js` | no | Presentation only (AD-10). Also serves the internal print route for PDFs (AD-18). |
| `api` | FastAPI on Uvicorn (Python 3.14) | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | no | Pre-deploy: `alembic upgrade head`. Health: `/api/health`. |
| `worker-ai` | same image as `api` | `python -m app.worker --queues ai-orders` | no | Only AI Orders and their 5-second rescue loop, so PDF work can never delay them (AD-5, AD-9). |
| `worker-batch` | same image as `api` | `python -m app.worker --queues llm-batch,reports-single,reports-bulk,mail --sweeper` | no | Everything else, plus the per-minute sweeper (AD-9). Has WeasyPrint system libraries. |
| Postgres 17 | Supabase project, eu-central-1 | — | no | App tables, procrastinate tables, LISTEN/NOTIFY. Connect via the **session pooler, port 5432** (the transaction pooler on 6543 breaks LISTEN). |
| Storage | Supabase Storage | — | no | One private bucket, `reports`. Downloads use short-lived signed URLs. |

Dropped compared with `technology.md`: Redis, the backup cron service, watchdog, the Cloudflare maintenance worker, the content, services and video services, Stripe, Vipps and Fiken. Redis is replaced by Postgres LISTEN/NOTIFY and procrastinate (AD-8, AD-9).

---

## 2. Accounts to create

| # | Service | Used for | Required? | Watch out for |
| --- | --- | --- | --- | --- |
| 1 | **GitHub** | repo, Actions CI, deploy trigger from the `production` branch | yes | The repo is **public**. Never commit `.env*` files except `.env.example`. |
| 2 | **Railway** | `proxy`, `web`, `api`, `worker-ai`, `worker-batch` in region **EU West (Amsterdam)** | yes | Check that your plan allows the EU region. Pin every service's region explicitly; a 2026 forum report describes a service moved region after an incident. |
| 3 | **Supabase** | Postgres and Storage in **eu-central-1 (Frankfurt)** | yes | Use a paid plan: free projects pause when idle and have no daily backups. Note the session pooler connection string. |
| 4 | **Domain + DNS** (for example Cloudflare DNS) | the public domain, and SPF, DKIM and DMARC for email | yes | Point the domain at the Railway `proxy` service. |
| 5 | **Resend** | Invitations, reminders, notifications, bounce webhooks (NFR-10) | yes in production | Verify the sending domain. Pick sending region **eu-west-1**. Account data is stored in the US, so list Resend as a sub-processor in the DPIA pack (spine, Deferred). |
| 6 | **LLM provider** | AI players, Debrief narration, Adapted items, AI assessment | when LLM mode is used | **The prototype decides the provider** (issues #8, #9). Requirements: EU region, zero data retention, no training, no router fallback (PRD §6.1, FR-68). If OpenRouter: in-region `eu.openrouter.ai` needs a Business or Enterprise plan. Use `zdr: true`, `data_collection: "deny"` and `allow_fallbacks: false`. |

---

## 3. Environment variables

### 3.1 `api`, `worker-ai` and `worker-batch` (shared core)

| Variable | Type | Where you get it | Notes |
| --- | --- | --- | --- |
| `APP_ENV` | 🟡🟢 | yourself | `local`, `test`, `ci` or `production`. In production the app refuses to start on missing or default secrets (AD-17). |
| `DATABASE_URL` | 🔴🟢 | Supabase → Connect → **Session pooler** | `postgresql+psycopg://…@…pooler.supabase.com:5432/postgres?sslmode=require`. One driver, psycopg 3, for both SQLAlchemy and procrastinate. |
| `DB_POOL_SIZE` | 🟡 | yourself | Start with `api` 10, `worker-ai` 5 and `worker-batch` 5, with no overflow. See the connection budget in section 5. |
| `JWT_SECRET` | 🔴🟢 | generate (64+ random bytes) | Signs the session cookie (AD-11). |
| `JWT_EXPIRE_MINUTES` | 🟡 | yourself | Default 43200 (30 days), as in `technology.md`. |
| `PUBLIC_BASE_URL` | 🟡🟢 | yourself | For example `https://olspillet.no`. Used in email links. |
| `WEB_INTERNAL_URL` | 🟡🟢 | Railway private networking | `http://web.railway.internal:3000`. The worker uses it to fetch the print route. |
| `BOOTSTRAP_ADMIN_EMAILS` | 🟡🟢 | yourself | Comma-separated. These users get the Admin role at first login (UJ-1). |
| `LOG_LEVEL` | 🟡 | yourself | `info` in production. Logs never contain names, emails or free text. |

**The pseudonym key is not an environment variable.** Someone other than the founder generates and keeps it (PRD §10), and types it in when a pseudonymised export is run (FR-71). The system stores only a fingerprint of it, to detect a changed key (AD-14). The same key must be used for the whole of a study.

### 3.2 Storage (Supabase)

| Variable | Type | Where |
| --- | --- | --- |
| `SUPABASE_URL` | 🟡🟢 | Project Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | 🔴🟢 | the same page. **Server only, never sent to the browser.** |
| `STORAGE_BUCKET_REPORTS` | 🟡 | default `reports`. The app creates the bucket if it is missing. |
| `SIGNED_URL_TTL_SECONDS` | 🟡 | default `300` (NFR-7: download links expire) |

Locally, without these keys, reports are written to `./.local-storage/` (mock, AD-17).

### 3.3 Email (Resend)

| Variable | Type | Notes |
| --- | --- | --- |
| `RESEND_API_KEY` | 🔴⚪🟢 | resend.com → API Keys. Empty = mails are only logged as `[email:mock]` (local only). |
| `EMAIL_FROM` | 🟡🟢 | for example `ØL-spillet <noreply@olspillet.no>` on the verified domain |
| `EMAIL_REPLY_TO` | 🟡 | optional |
| `RESEND_WEBHOOK_SECRET` | 🔴🟢 | Resend → Webhooks. Point it at `/api/webhooks/resend` for bounce and delivery events (FR-8). |

### 3.4 AI (provider decided by the prototype)

The **pinned model per Class session** (model version, provider, endpoint, region, Effort levels, timeouts) is data in the database, chosen by the Admin (FR-68). It is not an environment variable. The environment holds only credentials and global limits:

| Variable | Type | Notes |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | 🔴⚪ | only if OpenRouter is chosen |
| `OPENROUTER_BASE_URL` | 🟡 | `https://eu.openrouter.ai/api/v1` for EU in-region routing (Business or Enterprise plan). pydantic-ai's OpenRouter provider hardcodes the default URL, so the gateway must inject a client with this base URL. |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | 🔴⚪ | only if AWS Bedrock in an EU region is chosen |
| `AI_DEFAULT_SESSION_BUDGET_USD` | 🟡 | default cost limit for a new Class session (FR-69) |
| `AI_DAILY_ALERT_USD` | 🟡 | the Admin is alerted above this daily spend (FR-69) |

With no provider key, the gateway uses its deterministic mock: Rule-based Orders and code-only texts (AD-6, AD-17). In production, a Class session in LLM mode cannot be saved unless its pinned provider has a key.

### 3.5 Workers only

| Variable | Type | Notes |
| --- | --- | --- |
| `WORKER_CONCURRENCY` | 🟡 | per process. Start with `worker-ai` 40 and `worker-batch` 10. `ai-orders` needs about 3 per Replay played at the same time; tune it in the load test (NFR-3). |
| `REPORTS_SINGLE_RESERVED` | 🟡 | default `2`. Slots in `worker-batch` kept free for single reports while a ZIP builds (FR-57). |
| `AI_RATE_LIMIT_RPM` | 🟡 | per pinned endpoint, set from the provider's confirmed rate limit (AD-6, NFR-3). The value can also live in the model config. |

### 3.6 `web`

| Variable | Type | Notes |
| --- | --- | --- |
| `API_INTERNAL_URL` | 🟡🟢 | `http://api.railway.internal:8000`. Used only by the server-rendered print route, which fetches one report snapshot with a single-use render token (AD-18). |
| `NEXT_PUBLIC_APP_ENV` | 🟡 | build-time |
| `NEXT_PUBLIC_FEATURE_*` | 🟡 | build-time copies of the flags in 3.8 |

The browser calls relative `/api/…` paths only (single origin), so there is no API URL and no CORS config.

### 3.7 `proxy`

| Variable | Type | Notes |
| --- | --- | --- |
| `PORT` | 🟡 | set by Railway |
| `API_UPSTREAM` | 🟡 | `api.railway.internal:8000` |
| `WEB_UPSTREAM` | 🟡 | `web.railway.internal:3000` |

Caddyfile sketch:

```caddyfile
:{$PORT} {
  handle /api/* {
    reverse_proxy {$API_UPSTREAM} {
      flush_interval -1        # SSE: no buffering (AD-8)
    }
  }
  handle /print/* {
    respond 404                # the print route is internal only (AD-18)
  }
  handle {
    reverse_proxy {$WEB_UPSTREAM}
  }
}
```

### 3.8 Feature flags (PRD §8.1 cut list only, AD-17)

`FEATURE_STUDENT_CHOICE` (FR-21), `FEATURE_CROSS_INSTITUTION_STATS` (FR-65), `FEATURE_RERUN` (FR-66), `FEATURE_INFO_VISIBILITY` (FR-83), `FEATURE_LECTURER_TEST_GAME` (FR-87), `FEATURE_GAME_DATA_EXPORT` (FR-88), `FEATURE_CAPACITY` (FR-12 capacity). Default `true` locally. In production, set them per readiness before the pilot.

### 3.9 Local Docker Compose

`COMPOSE_PROJECT_NAME=olspillet`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `HTTP_PORT` (default 8080). Compose starts `postgres:17`, `api`, `worker-ai`, `worker-batch`, `web` and `proxy`. You need no keys: every integration runs as a mock, and a seeded demo Class with an Admin, a Lecturer and 8 Students is created when the database is empty (`APP_ENV=local` only).

---

## 4. Railway configuration

- **Project:** `olspillet`, environment `production`. Add a `staging` environment with its own Supabase project before the rehearsal (spine, Deferred).
- **Region:** EU West (Amsterdam) on every service.
- **Builds:** one Dockerfile per image. `api/Dockerfile` (Python 3.14 slim plus the Pango and HarfBuzz fonts WeasyPrint needs) is used by `api`, `worker-ai` and `worker-batch`, always from the same commit (AD-24). Also `web/Dockerfile` (multi-stage `node:24`, `next build`, standalone) and `proxy/Dockerfile`. Use `watchPatterns` per service so a web-only change does not redeploy the api.
- **Deploy:** the `production` branch auto-deploys; `main` is the working branch (`technology.md`). The `api` pre-deploy command is `alembic upgrade head`. Migrations are expand-then-contract, so the old and new code can run side by side during a deploy (AD-24).
- **Health checks:** `api` `/api/health` (checks the DB). `web` `/`. `proxy` `/api/health` through itself. Use overlap and draining seconds for zero-downtime deploys during Lab hours.
- **Private networking:** `api`, `web` and the two workers are reachable only on `*.railway.internal`, and only `proxy` has a public domain.

## 5. Supabase configuration

- Region **eu-central-1**, Postgres 17 (or the project default if higher).
- **Connection budget.** The session pooler's default pool size is 15 on the small plans, and every open connection holds one slot. Count per process: the SQLAlchemy pool, procrastinate's own pool (at least 4) and one LISTEN connection for `api`. That is about 35 with the starting numbers, and double during a deploy overlap. Raise the pool size in Supabase (Database → Connection pooling) to fit, and pick a compute size that allows it.
- Connections use the **session pooler (5432)** only. Do not use the 6543 transaction pooler, because it breaks LISTEN/NOTIFY and procrastinate.
- Keep daily backups on. Before the pilot, turn on point-in-time recovery, with a target of at most 5 minutes of lost data and 1 hour to restore (NFR-4; an assumption in the spine's Deferred list).
- Create the bucket `reports` as **private**, or let the app create it at first use.
- Do not enable Supabase Auth or the Data API: auth is the app's own (AD-11), and nothing talks to the database except `api` and the two workers.

## 6. CI (GitHub Actions)

1. `api`: `uv sync --locked`, ruff, pytest with a Postgres 17 service, and engine golden traces.
2. `web`: `npm ci`, typecheck, Vitest, then build. `package.json` needs the override `{"overrides": {"openapi-typescript": {"typescript": "6.0.3"}}}`, because openapi-typescript 7.13 still declares TypeScript 5.
3. Contract check: export FastAPI's OpenAPI, regenerate the TS client, and fail on diff (AD-10).
4. Copy check: fail if pre-Debrief copy contains «Beer Game» or «bullwhip» (AD-19).
5. Playwright with axe at 320, 360 and 1440 px, and at 400 % zoom, against `docker compose` (NFR-6).
6. veraPDF check of one sample Student report (PDF/UA).
7. Simulation smoke run: `python -m app.sim` plays a few all-AI Games on the mock provider (AD-22).

---

## 7. Checklist before the first Class session

1. Generate **new** values for every 🔴 variable. Never reuse keys from other projects.
2. Someone other than the founder generates and holds the pseudonym key, outside Railway (PRD §10, AD-14).
3. Supabase on a paid plan in eu-central-1, with point-in-time recovery on. Railway services pinned to EU West.
4. Resend domain verified (SPF, DKIM, DMARC), region eu-west-1, bounce webhook registered and tested.
5. LLM provider chosen by the prototype, which is the simulation runner `python -m app.sim` (AD-22). Terms (EU region, ZDR, no training) and the rate limit confirmed in writing. Model pinned and tested on all-AI runs (FR-68, PRD §10).
6. `APP_ENV=production`, and confirm that the app refuses to start with one secret removed (AD-17).
7. Sub-processor list for the DPIA pack: Railway, Supabase, Resend, the LLM provider and the DNS provider.
8. A restore drill from a Supabase backup into a scratch project, and an error-tracking or uptime tool chosen (spine, Deferred).
9. A load test of 250 simultaneous players including provider rate limits (NFR-3).
10. The `staging` environment has been used for the rehearsal Class session and the Control test.
