# IRIS onE application engine

Run these commands from this directory (the `adarsh maurya` folder):

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/ and sign in or create an account. API documentation is at `/docs`. No external keys are required for SQLite storage, local retrieval, application instructions, tracking or calendar downloads. Anonymous requests use the shared sample student; use authenticated accounts for personal profiles and application records.

The existing layout and routes are retained. The catalog now supplies the application modal, persistent document checklist, policy conflict warnings, match scores and calendar export. Ask Iris retrieves up to five local records using deterministic vectors and keyword/category matching. It never launches web scraping during a chat or feed view. Existing `/api/assistant/chat` clients remain supported.

## Configuration

Copy `.env.example` to `.env` and fill only the optional settings you need:

- `TINYFISH_API_KEY` and `GEMINI_API_KEY` enable the live discovery, render, Apply-button inspection and schema extraction pipeline. A failed or blocked stage retains the cached information.
- The assistant tries configured Gemini, Groq and Ollama models in that order, then uses deterministic local synthesis if they fail. Provider access, free-tier availability and quotas depend on the configured account. No key means no cloud inference calls.
- `DATABASE_URL=postgresql://...` selects PostgreSQL. The schema uses pgvector when the extension is available, with JSON vectors as a portable fallback. An unavailable PostgreSQL connection at startup falls back to SQLite. After PostgreSQL is established, connection failures are surfaced instead of silently splitting writes into another database.
- `DATABASE_PATH` selects a SQLite file, otherwise `backend/iris_one.db` (or `/data/iris_one.db` on a mounted volume) is used in WAL mode.
- Set `JWT_SECRET` to a strong random value for deployment. The existing local demo secret is only for development.

APScheduler starts with the FastAPI lifespan and runs every 12 hours. An OS lock selects one scheduler owner per local database; a renewable database lease prevents concurrent sync jobs across processes or hosts. Run the service continuously on persistent storage for unattended refreshes. `IRIS_DISABLE_SCHEDULER=1` disables scheduling for tests. Manual sync returns HTTP 202 and runs in the background.

## APIs

- `GET /api/sync/status`: recorded sync result, last actual live verification and next-run countdown.
- `POST /api/sync/trigger`: `{"live": true}` or an offline cache check with `{"live": false}`.
- `POST /api/assistant/ask`: `{"query": "How do I apply for Airtel?", "student_id": "default_student", "opportunity_id": "airtel"}`. Opportunity focus is optional. Signed-in requests automatically select the caller's profile; another student's ID is rejected.
- `GET /api/opportunities/{id-or-slug}/how-to-apply`: channels, numbered guide, required documents, match breakdown, gate warnings, policy conflict, verification provenance and saved checklist.
- `POST /api/applications/track`: `{"opportunity_id": "airtel", "status": "In Progress", "checked_documents": []}`. Status may be `Saved`, `In Progress` or `Applied`. Writes are idempotent and update existing dashboard application counts for signed-in users.
- `GET /api/applications/tracked`: restore the caller's tracked applications and checklist state.
- `GET /api/opportunities/{id-or-slug}/calendar.ics`: RFC 5545 export with escaped/folded UTF-8 lines and 72-hour/24-hour alarms. A missing deadline returns HTTP 409 rather than inventing a date.
- `PUT /api/auth/profile` also accepts `class_12_pct`, `family_income_inr` and `nirf_top_50` to confirm eligibility inputs. A college name alone does not prove a NIRF ranking.

Resume uploads support PDF, DOCX and TXT. Parsed profiles and resume text are stored for the selected student and used by subsequent retrieval. Existing opportunity IDs and foreign keys are preserved; public slugs provide the stable text IDs without destructively replacing the old numeric primary keys.

## Catalog provenance

Seed records are reference information, not evidence that an application is currently open. Existing past deadlines are retained and excluded from the active feed. Named assistant queries and application guides can still inspect archived opportunities.

An offline pass records `last_checked_at`, recomputes embeddings and marks the remote pipeline stages as skipped. It does not advance `last_verified_at`. Only a successful live Apply-button check plus validated extraction produces `VERIFIED_LIVE` and an `Apply Live` channel badge. Adobe and Google student benefits can vary by region and cycle; the guide asks the student to confirm current pricing, availability and renewal terms. Exclusive-tuition warnings describe cached program rules and are not a substitute for the current official terms.

## Validation

```powershell
python -B -m unittest discover -s backend -p test_backend.py -v
python -B backend/legacy_smoke.py
node --check frontend/js/app.js
npm install --no-save playwright
npx playwright install chromium
node scripts/test_ui.cjs
```

The backend suite and original route smoke checks use disposable databases and no billed provider calls. Browser checks cover offline assets, guide steps, checklist persistence, tracking, conflicts, calendar download, chat and mobile sizing. Set `PLAYWRIGHT_CHANNEL=chrome` to use an installed Chrome browser. A separate integration test runs with `IRIS_TEST_POSTGRES_URL` pointing to a disposable pgvector database; the GitHub workflow provisions one automatically.

The interface uses checked-in compiled Tailwind CSS so the external styling CDN is not required. Rebuild after changing utility classes:

```powershell
npm exec --yes --package=tailwindcss@3.4.17 -- tailwindcss -c tailwind.config.cjs -i frontend/css/tailwind.source.css -o frontend/css/tailwind.css --minify
```

The 50 ms retrieval target in the brief depends on catalog size, database and hosting hardware; this change does not claim a measured production service-level guarantee.
