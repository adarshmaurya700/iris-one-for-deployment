# Audit fixes and validation — 31 October 2026

The local demonstration works with the existing architecture and visual identity retained. **Full live verification is not ready to claim:** Gemini is unconfigured and the real TinySearch probe rejected the available credential with HTTP 401. No Fetch/Agent call followed that failure. No cloud deployment was performed.

## Technical audit and fixes

Initial issues, severity, source evidence and intended fixes are in [AUDIT.md](AUDIT.md). All thirty findings received code/configuration/documentation changes; external validation limits remain explicit below.

- **A01–A05, A23: authentication/request security.** Removed the stored-hash/plaintext login bypass and public signing secret. Enforce password byte limits, required JWT claims, strong production signing/admin secrets, calendar ownership, admin protection and request limits. Forwarded headers cannot reset application limits. Same-origin CORS is default, wildcard credentials are disabled, API responses are not cached and CSP/referrer/permissions headers are present.
- **A06–A12, A20: truthful integrations.** Removed fabricated-success legacy verification and health/sample claims. TinyFish makes bounded calls without implicit billed retries and validates per-URL content, completion and application evidence. Private destinations are rejected. Gemini calls share header credentials, timeouts, fence-aware JSON parsing and redacted diagnostics. Omitted extraction fields cannot erase known dates/criteria. Badges expire after twelve hours even without the scheduler. Configured, successful, failed, cached and fallback states differ.
- **A13–A19, A28: personal data, matching and Ask IRIS.** Live guests start blank; labeled demo disables provider calls. Resume parsing no longer fabricates identity, income, marks, skills or completeness. Corrupt/oversized/unreadable documents reject. One 35/25/25/15 matcher serves every view without a score floor. Missing facts remain unknown; expired records are not eligible. Marks/income/ranking are editable. Retrieval uses profile compatibility and deadline intent; cloud context excludes raw resumes/email/vectors and keeps retrieved data outside system instructions. Legacy chat uses the same scoped engine without surprise URL discovery.
- **A21–A22, A29: calendar and data ownership.** Shared RFC 5545 generation escapes/folds content and returns 409 for unknown dates. Private feeds require ownership. Telegram preview reports no delivery, requires authentication and forbids arbitrary recipients. Workspace export and scoped resume removal work. No notification was sent.
- **A24–A27: repository/deployment hygiene.** Backed up SQLite before changes. Untracked databases/WAL/cache files and 4,614 installed dependency artifacts, preserving local files. Removed unused Express/Anthropic dependencies; pinned Playwright remains development tooling. Patched multipart requirements and aligned Python entry points. A FastAPI launcher replaces the broken Streamlit alias. Docker is non-root and excludes private/runtime artifacts. Render uses main, correct app root and a disk-capable plan. Removed unsupported performance/accuracy claims and unsafe historical proof tooling.
- **A30: restrained UI refinement.** Updated paper/nav/text/blue/champagne tokens and reduced decorative effects. All eight views and responsive navigation remain. Backend eligibility drives detail checks; technical traces stay internal. Mode labels, refresh language and new data controls are functional.

## Integration status

| Service | Status | Evidence and limits |
| --- | --- | --- |
| Gemini | **Not configured; live untested** | No GEMINI_API_KEY. Mocked success, fenced/malformed JSON, outage and cascade behavior tested. Actual account/model availability cannot be confirmed. |
| TinyFish | **Failed** | One real TinySearch call returned HTTP 401. Live Fetch/Agent are **untested** because the probe stopped. Mocked content/completion/no-retry tests passed. |
| Ask IRIS | **Working locally** | Scoped retrieval, stored sources, eligibility/conflicts, score explanation, SSE and local fallback passed. Cloud/Ollama success is mocked, not a real inference claim. |
| Database | **Working: SQLite and PostgreSQL/pgvector** | SQLite persistence/ownership/restart tests passed locally. Disposable PostgreSQL/pgvector HTTP, schema and vector integration passed in GitHub CI. No local PostgreSQL service was configured. |
| Authentication | **Working locally** | Signup/login, bcrypt, byte limits, rejecting hashes/forged tokens, account/guest isolation, calendar ownership and production guards passed. Not an independent penetration test. |
| Scheduler | **Working locally** | 43,200-second interval, owner/lease exclusion, offline sync and start/stop passed. No twelve-hour provider soak or production failover benchmark. |
| Resume extraction | **Working locally** | TXT/DOCX/PDF parsing/persistence passed; malformed/empty/oversized/compressed expansion cases reject. Gemini live extraction is **untested**. Image-only PDF OCR is unsupported. |

[Redacted real probe evidence](integration-evidence.json) records the actual timestamp and authentication failure, not program availability.

## Executed checks

Before edits: 24 backend tests, original 27-route smoke workflow, JavaScript syntax and Playwright desktop/mobile checks passed. The audit found gaps despite this baseline.

After fixes:

- `python -B -m unittest discover -s backend -p 'test_*.py' -q`: **60 discovered, 59 passed, 1 skipped** locally. PostgreSQL skipped without a disposable URL.
- `python -B backend/legacy_smoke.py`: compatibility route workflow passed with corrected ownership/preview assertions and no invented calendar dates.
- `node --check frontend/js/app.js`: passed.
- Playwright 1.64.1 with installed Chrome: passed eight exclusive views; search/filter/save; failure recovery; details/dialog; persisted documents/statuses; calendar downloads; Markdown/SSE sources; resume upload/removal; eligibility inputs; both wizard steps; mode label; preferences; export; authentication/account isolation; keyboard search and mobile overflow.
- Browser checks blocked external assets to exercise poor venue connectivity. Desktop profile/feed and responsive screenshots were inspected. No browser JavaScript errors were reported.
- `pip-audit`: **31 resolved distributions, zero known reported vulnerabilities**. [Result](dependency-audit.json).
- `npm audit`: **zero known reported vulnerabilities**. [Result](npm-audit.json).
- Python parsing and Git whitespace checks passed. Docker/Render/Railway configuration was reviewed but not executed/deployed locally.

GitHub CI subsequently passed **both backend/browser and PostgreSQL jobs** for implementation commit `592be0cde4cc77fb24a78e3c62ba913685334cf8`: [verified workflow run](https://github.com/adarshmaurya700/iris-one-for-deployment/actions/runs/41175834608). This adds Linux/Python 3.11, actual Chromium and disposable PostgreSQL/pgvector coverage to the local checks. This report update changes documentation only.

Warnings: current Starlette TestClient httpx deprecation and an intentionally forged old short JWT key in a rejection test. Neither is suppressed in application code.

## Remaining limitations

1. Replace the rejected TinyFish credential and configure Gemini before claiming live discovery/verification. Provider/account quotas and the full live pipeline remain unverified. Restricted sources are not bypassed.
2. PostgreSQL passed its disposable CI check. Docker image execution still needs a capable host. No deployment, independent penetration test, concurrency benchmark or sustained provider soak was performed.
3. Fixtures/cached terms do not prove current eligibility, pricing, availability or award-combination permission. Self-reported student facts do not replace official document review.
4. Local parsing is conservative and has no OCR. Students should review extraction. Configured Gemini resume extraction sends supplied text to the provider.
5. Limits/diagnostics are process-local. Multiple replicas need shared limiting and durable monitoring. The separate provider-probe process has its own retained report.
6. Logout removes the browser token but does not revoke a copied token; access tokens expire after 24 hours. Guest cookies expire after seven days. Account deletion, password reset and email verification are not implemented.
7. Prior Git history was not rewritten and can still contain historical runtime data/key fragments. Future commits exclude them. Original desktop edits remain untouched.

## Official references

- [TinyFish official cookbook](https://github.com/tinyfish-io/tinyfish-cookbook): Search/Fetch REST contracts and browser-agent surfaces. Installed official Python SDK 0.9.0 was inspected too.
- [Gemini 2.5 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash) and [structured output](https://ai.google.dev/gemini-api/docs/generate-content/structured-output): documented capabilities; real account availability still needs a credentialed call.
- [python-multipart security advisory](https://github.com/Kludex/python-multipart/security/advisories/GHSA-59g5-xgcq-4qw3): affected versions below 0.0.18; requirements now use at least tested 0.0.32.
- [Render persistent disks](https://render.com/docs/disks): require paid compatible services; ephemeral files are lost on redeploy/restart.

See [deployment instructions](DEPLOYMENT.md), [demo walkthrough](DEMO_GUIDE.md) and [architecture](ARCHITECTURE.md).
