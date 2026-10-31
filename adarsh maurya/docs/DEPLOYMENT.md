# Running and deploying IRIS onE

## Local deterministic demonstration

From the repository root, open PowerShell:

```powershell
Set-Location 'adarsh maurya'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
$env:IRIS_MODE = 'demo'
$env:IRIS_ENV = 'development'
$env:DATABASE_PATH = Join-Path $env:LOCALAPPDATA 'IRIS-one/iris_demo.db'
.\.venv\Scripts\python.exe -B -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/. Demo mode is prominently identified. It seeds reference fixtures, supplies a sample guest profile, and disables external AI/verification calls even if keys exist. It never fabricates successful live verification. Account creation, uploaded resumes, saved items, application statuses and checklists still persist. Existing reference dates are never rolled forward to make a program appear open.

The optional `.env.example` can be copied to `.env`; host environment variables take precedence. Development creates a random persistent `.jwt-secret` in the application data directory outside Git. Keep this file if you want development sessions to remain valid.

## Local live mode

Use a separate database from the demo. Supply credentials in your shell or ignored `.env`, never frontend code or Git:

```powershell
$env:IRIS_MODE = 'live'
$env:DATABASE_PATH = Join-Path $env:LOCALAPPDATA 'IRIS-one/iris_live.db'
# Set GEMINI_API_KEY and TINYFISH_API_KEY securely before starting.
python -B -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
```

A new live database starts empty. Populate it with a genuine successful Scan & Verify operation. Existing databases are retained. `IRIS_SEED_REFERENCE=1` explicitly opts into historical reference fixtures for testing; these remain unverified. Guests start blank in live mode. Switching modes issues a new guest cookie; signed-in accounts retain their data.

`GEMINI_MODEL` defaults to `gemini-2.5-flash`. `GROQ_API_KEY` and `OLLAMA_BASE_URL` optionally enable the assistant cascade after Gemini; `OLLAMA_MODEL` defaults to `llama3.2`. Local deterministic retrieval remains available without these services. Full verification requires both working Gemini and TinyFish credentials; absent configuration does not start a partial billed pipeline.

## Production configuration

Set these values on the hosting service:

- `IRIS_ENV=production`
- `IRIS_MODE=live`, or explicitly `demo` for a labeled public demonstration.
- `JWT_SECRET`: at least 32 random bytes; generate independently of the admin key.
- `IRIS_ADMIN_KEY`: at least 32 random bytes, kept server-side.
- `DATABASE_PATH=/data/iris_one.db` on a persistent mounted volume, or `DATABASE_URL=postgresql://...` for a managed database.
- `ALLOWED_ORIGINS=` for same-origin hosting. For a separate frontend, list exact HTTPS origins separated by commas. Wildcards are rejected in production.
- Provider credentials for capabilities you intend to demonstrate, held in the hosting secret store.

Generate secrets with a cryptographically secure password generator and store them in the service's secret manager. Missing/weak production secrets cause startup to fail. Old tokens signed with the former public development key are invalidated; accounts and database data are preserved and users can sign in again.

Run one Uvicorn worker per instance for this demo deployment. Rate limits are process-local; multiple replicas require a shared limiter or a rate-limiting reverse proxy. Configure Uvicorn proxy trust only for actual trusted proxy IPs. Serve production through HTTPS. Guest cookies are Secure in production.

```sh
python -m uvicorn main:app --app-dir backend --host 0.0.0.0 --port "$PORT" --workers 1
```

Production fails safely if configured PostgreSQL cannot connect. Development may fall back at initial connection only; an established PostgreSQL connection never silently switches writes to SQLite. pgvector failure uses the same database's JSON vectors rather than another database.

## Docker

From repository root:

```sh
docker build -f "adarsh maurya/Dockerfile" -t iris-one "adarsh maurya"
docker volume create iris-data
docker run --rm -p 8000:8000 --env-file /secure/path/iris-production.env -v iris-data:/data iris-one
```

The image runs as UID 10001 and excludes databases, caches, environment files, uploads and installed Node dependencies. Ensure a bind mount at `/data` is writable by UID 10001. Docker execution was unavailable on the audit machine; validate the image on your Docker host before deployment.

## Render and Railway

The repository-root `render.yaml` specifies `main` and `rootDir: adarsh maurya`. Its SQLite disk requires a paid disk-capable plan, as documented by [Render](https://render.com/docs/disks). The matching file inside the app directory is retained for existing Blueprint setups. Secrets are generated or configured in Render.

For Railway, select service root `adarsh maurya`, use its existing `railway.json` and Dockerfile, mount a persistent volume at `/data`, and set the production variables above. Managed PostgreSQL is an alternative. No deployment was triggered by this audit.

## Diagnostics and operations

`GET /api/health` is the public database/liveness check; it omits user counts and filesystem paths. `GET /api/admin/diagnostics` requires `X-IRIS-Admin-Key` in production and reports redacted provider states, database connectivity and scheduler status. It contains no API keys, prompts or resume text. A direct loopback caller can inspect diagnostics without a configured admin key in development. Technical traces are separate from student detail views.

Run a bounded provider check manually:

```sh
python -B scripts/check_integrations.py
python -B scripts/check_integrations.py --live --output /secure/path/integration-check.json
```

Without `--live`, no network operation occurs. With it, there is at most one Gemini request and one Search, Fetch and Agent request. Operations stop on failure, never retry a potentially accepted billed automation, never submit forms or sign in, and never update opportunity verification. The audit's real check failed at TinySearch with HTTP 401; Fetch/Agent were not attempted. Gemini was not configured. Replace/configure credentials and rerun locally to establish live readiness.

APScheduler checks every 12 hours with an OS owner lock and transactional database lease. Public badges expire on reads even if the scheduler stops. `IRIS_DISABLE_SCHEDULER=1` disables unattended checks for tests. A live badge lasts at most 12 hours and requires a valid non-future timestamp and an open, non-expired application.

## Data and backups

Back up SQLite using its online backup API; do not copy a running database without its WAL. The audit created online backups under `%LOCALAPPDATA%/IRIS-one/backups/` before changes. Back up PostgreSQL through the provider or `pg_dump` before migrations. Keep backups, resumes, databases and `.env` files outside Git and container images.

Runtime files were removed from future Git tracking without deleting their local copies. Prior Git history remains unchanged and can contain historical data/partial credentials. Replace the old TinyFish credential: its live check failed and an old proof artifact included a fragment. No history rewrite was performed.
