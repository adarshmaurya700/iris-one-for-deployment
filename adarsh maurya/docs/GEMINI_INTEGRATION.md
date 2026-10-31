# Gemini configuration and real verification — 31 October 2026

**The local application now uses `GEMINI_MODEL=gemini-3.1-flash-lite`, with real Gemini generation, opportunity extraction, resume analysis and Ask IRIS verified.** The credential is stored only in ignored `backend/.env.local`, read through the environment loader, and protected with a Windows ACL restricted to the current user. Its value is absent from this report, source, logs and Git.

## Model access results

- **gemini-2.5-flash — failed generation.** Authenticated model metadata and listing returned HTTP 200, but the actual `generateContent` request returned HTTP 404 / `NOT_FOUND`. Google's response says this model is unavailable to new users and recommends 3.8 Flash. Metadata/listing alone does not establish inference access.
- **gemini-3.8-flash — generation not verified.** It appears in the authenticated model list. A generation request returned HTTP 503 / `UNAVAILABLE` (temporary high demand); a subsequent controlled attempt with supported parameters reached the read timeout. This is not evidence of a permanently unavailable model, but it is insufficient to configure it as working.
- **gemini-3.1-flash-lite — real generation succeeded.** It is listed for this credential, returned successful model metadata, and passed real inference plus application function checks. It was explicitly selected locally after these checks; there is no automatic model-switching code.

`runtime_config.gemini_model()` is the single model selector. The previous 2.5 Flash default is retained for compatibility with existing projects. The local configuration and example configuration explicitly select the tested alternative. A different model can be chosen through `GEMINI_MODEL`; the client normalizes an optional `models/` prefix and rejects URLs/invalid IDs.

## Function results

- **Authentication and environment loading: succeeded.** The supplied credential authenticated to Google's official model endpoints and real generation. It is sent only as the `x-goog-api-key` header to the official API, never in query strings or frontend code.
- **Structured opportunity extraction: succeeded on a real Google response.** Gemini extracted GitHub Education facts from a paraphrase of the [official requirements](https://docs.github.com/en/education/about-github-education/github-education-for-students/apply-to-github-education-as-a-student). The JSON passed Pydantic validation, preserved the 13-year minimum, and left the unspecified deadline null. An initial request returned 503 and correctly produced a local fallback; the retained recheck succeeded. Extraction intentionally reports `is_verified_active=false` / `VERIFICATION_PENDING` because it does not inspect a live application action.
- **Resume analysis and FastAPI multipart upload: succeeded.** `/api/resume/analyze` sent a synthetic test resume to Gemini in a disposable SQLite database. The response identified `google_gemini` and the actual model, recovered the supplied name and Python/FastAPI/SQL skills, and persisted the result. This was a real provider call, not a mocked response or a real student's private resume.
- **Ask IRIS: succeeded.** `/api/assistant/ask` returned `LIVE_SUCCESS`, the configured Gemini model, an answer and stored source cards in the disposable database. A separate request to the restarted application at `http://127.0.0.1:8000` also returned HTTP 200 / `LIVE_SUCCESS` with that model. The local app is in live mode.
- **Local fallback: regression tested.** Missing credentials, demo mode, retired models, malformed JSON, invalid schemas, transient rejection and timeouts remain distinct from real Gemini success. Both extraction functions return provider/model/source metadata; fallback results identify the local parser and safe upstream status.
- **Full TinyFish + Gemini application verification: not tested in this task.** TinyFish previously returned HTTP 401. No TinyFish call, program-availability claim, scheduled verification batch or database schema migration was performed here. Unattended verification is disabled for the local preview during Gemini testing.

## Code changes

- Removed import-time key capture, unused hardcoded endpoint constants, model-name-based provider routing and duplicated schema hints. All production Gemini requests use the shared configurable client.
- Added Gemini JSON Schema output contracts and Pydantic validation for opportunity/profile extraction. Explicit income and minimum age are retained; unknown facts remain absent/null.
- Model-specific request settings omit deprecated sampling parameters for Gemini 3.6+ and use supported low thinking for 3.8. Existing 2.5 settings stay compatible.
- Added one bounded same-model retry for explicit HTTP 429/503 responses, with a two-second delay and a 45-second total request ceiling. `GEMINI_MAX_RETRIES=0` disables it. Authentication/client/model errors and ambiguous timeouts are not retried; no model is substituted automatically.
- Diagnostics retain safe HTTP status, API status/reason, model and attempt count. They do not log upstream messages, request content, headers or credential values.
- Existing FastAPI routes and SQLite/PostgreSQL schema are unchanged. Added `scripts/check_gemini.py` for deliberate reproducible real checks using disposable data, plus focused provider/schema/security regression tests.

## Reproduce safely

Configure `GEMINI_API_KEY` securely in the environment or ignored backend `.env.local`, and set `GEMINI_MODEL` explicitly. Then, from the app directory:

```sh
python -B scripts/check_gemini.py --live --model gemini-3.1-flash-lite --output /secure/path/gemini-report.json
```

This script deliberately makes a small set of real generation requests and uses a disposable SQLite database. It makes no TinyFish call and never switches models. The regular unit/browser suites mock or disable providers and do not spend provider quota.

Evidence retained without credentials:

- [Authenticated model metadata/list](gemini-initial-probe.json).
- [First real function run](gemini-live-evidence.json), including the initial opportunity 503 fallback and successful resume/assistant calls.
- [Successful opportunity recheck](gemini-opportunity-recheck.json).
- [Running FastAPI application check](gemini-running-app-evidence.json).

New automated coverage checks configurable model routing, modern parameters, no model substitution on 404, bounded retries, no retry after timeout, JSON Schema, real/fallback provenance and redacted errors/logs. Remaining limits: provider load/quota can cause later failures, and successful extraction is not proof of current program availability.

## Official documentation consulted

- [Google API key handling](https://ai.google.dev/gemini-api/docs/api-key).
- [Model metadata/list API](https://ai.google.dev/api/models) and [troubleshooting](https://ai.google.dev/gemini-api/docs/troubleshooting): metadata does not establish generation entitlement; retry only appropriate transient failures.
- [Gemini 3.8 migration parameters](https://ai.google.dev/gemini-api/docs/latest-model): omit deprecated sampling settings; `minimal` thinking is unsupported on 3.8.
