# IRIS onE

**Better Opportunities. A Brighter You.**

A student workspace for opportunity discovery, profile compatibility, application guides, saved items and deadlines. FastAPI, SQLite/PostgreSQL, HTML, CSS and vanilla JavaScript; optional Gemini and TinyFish services.

## Run locally

From this directory in PowerShell:

```powershell
python -m pip install -r backend/requirements.txt
$env:IRIS_MODE = 'demo'
$env:DATABASE_PATH = Join-Path $env:LOCALAPPDATA 'IRIS-one/iris_demo.db'
python -B -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/. The labeled demo runs without external keys: authentication, two-step onboarding, resume extraction, four-factor scoring, saved items, checklists/statuses, streamed local Ask IRIS and calendar exports. Sample records do not prove live availability.

Use `IRIS_MODE=live` with a separate database for genuine provider operations. New live databases start empty and guests start blank. At the 31 October 2026 audit Gemini was unconfigured and the available TinyFish credential returned HTTP 401. Full live verification remains unvalidated. No production latency, accuracy or scalability guarantee is claimed.

## Documentation

- [Technical audit](docs/AUDIT.md)
- [Fixes, service status and test evidence](docs/VALIDATION.md)
- [Exact setup and deployment instructions](docs/DEPLOYMENT.md)
- [Hackathon walkthrough and Q&A](docs/DEMO_GUIDE.md)
- [Architecture](docs/ARCHITECTURE.md)

Production requires independent strong JWT/admin secrets, HTTPS and persistent storage. Secrets, databases, resumes and caches stay outside Git. No deployment was triggered.

## Checks

In `adarsh maurya`:

```sh
python -B -m unittest discover -s backend -p 'test_*.py' -v
python -B backend/legacy_smoke.py
node --check frontend/js/app.js
```

From repository root:

```sh
npm ci
npx playwright install chromium
npm run test:ui
```

Set `PLAYWRIGHT_CHANNEL=chrome` to use installed Chrome. Tests use disposable databases and mocked providers. PostgreSQL requires a disposable `IRIS_TEST_POSTGRES_URL`; CI provisions pgvector. The separate manual `scripts/check_integrations.py --live` probe requires real credentials.
