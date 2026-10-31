# IRIS onE audit — 31 October 2026

Scope: the repository source, deployment configuration, dependency manifests, frontend contracts, legacy APIs, tests, catalog fixtures and tracked runtime artifacts. Existing architecture and eight-view navigation are retained. No automatic deployment is authorized.

Baseline (before source edits): 24 backend tests passed; original 27-route smoke script passed; JavaScript syntax and Playwright interaction/mobile checks passed. Passing these checks did not establish external-provider correctness. Gemini credentials and a disposable PostgreSQL URL were absent. A TinyFish credential was present (value never recorded).

## Prioritized action plan

1. Close authentication/authorization and public billing controls; preserve student data and back it up.
2. Make provider and verification provenance truthful, bound external requests, and add internal diagnostics and explicit live/demo modes.
3. Unify matching, eligibility and profile/resume handling; test missing/contradictory information and persistence.
4. Repair deployment/packaging, refine the existing UI, expand regression coverage, and publish reproducible reports and a demonstration guide.

## Initial findings and intended fixes

- **A01 Critical — predictable signing key.** `backend/auth.py` defaults to a public 24-byte secret and suppresses warnings. Require a strong production key and a persistent random development key.
- **A02 Critical — stored-hash login bypass.** `verify_password` accepts `password == password_hash`. Remove plaintext equality; enforce bcrypt input limits and authentication rate limits.
- **A03 High — calendar IDOR.** `/api/users/{user_id}/calendar.ics` requires no authentication. Require the matching account; reuse validated calendar generation.
- **A04 High — public shared-catalog and billing mutations.** Admin refresh, manual sync and verification GET lack consistent authorization/rate controls. Protect admin operations and apply limits on every expensive entry point.
- **A05 High — rate-limit bypass.** The limiter trusts arbitrary `X-Forwarded-For`, retains unbounded IP keys, and `/api/assistant/ask` lacks a limiter. Use the server-established client address, bound state and cover both assistant routes.
- **A06 High — synthetic verification success.** Legacy `tinyfish_pipeline.py` has completed mock stages, invented timestamps/scores, and a failure branch returning `is_verified=True`. Route compatibility functions through the honest verification service; isolate explicitly simulated demo fixtures.
- **A07 High — live badge never expires.** Stored `VERIFIED_LIVE` and channel flags have no freshness check. Derive public badges from actual timestamps and the 12-hour freshness window.
- **A08 High — TinyFetch response validation missing.** The existing `urls: [url]` request is correct, but HTTP success with per-URL errors or empty rendered content is not checked. Normalize and validate rendered content.
- **A09 High — duplicate billed agent runs.** Any SDK exception retries REST automatically. Use one bounded official request, validate completion and evidence, and never retry a possibly accepted automation implicitly.
- **A10 High — unsafe scanning URLs.** Scheme-only URL checks allow loopback/private/local addresses and untrusted extracted application URLs. Validate public destinations and source/application domain consistency without bypassing access restrictions.
- **A11 High — conflicting environment loaders.** TinyFish uses `override=True` and providers capture credentials at import. Use one non-overriding loader and read configuration at request time.
- **A12 High — model failures lose provenance.** Provider exceptions are swallowed, extractor uses API keys in query strings, and JSON parsing assumes one response shape. Centralize safe diagnostics, header authentication, bounded parsing and explicit fallback states.
- **A13 High — resume fabricates identity/eligibility.** Local fallback invents Adarsh's name, age, institution, Delhi, 86% and income for arbitrary uploads; normalization claims 92% completeness. Extract only supported facts, preserve unknown values and compute actual completeness.
- **A14 High — corrupt uploads accepted.** PDF/DOCX parse failures decode binary garbage; no-file requests use a sample; JSON and compressed document content are not bounded. Validate content and limits and require explicit sample use.
- **A15 High — incomplete eligibility marked passed.** Missing marks/income pass checklist tests and income defaults to 6/8 LPA. Use confirmed/unknown/failed checks without assumed financial eligibility.
- **A16 High — inconsistent match engines.** Provider presence selects different scoring; old scores are clamped to 65–99. Use one 35/25/25/15 engine across feed, details, saved, matching and assistant.
- **A17 High — shared sample identity leaks into guests.** All new guests receive the same demo profile; `/match` can use `default_student` outside the guest context. Use blank isolated guest profiles in live mode and explicit demo fixtures.
- **A18 High — legacy assistant diverges.** It accepts client profile overrides, performs surprise URL discovery, and has separate provider logic. Keep its response contract backed by the same scoped retrieval and model cascade.
- **A19 Medium — retrieval ignores date and personal rank.** Generic results can include expired active flags, are not ranked by student compatibility, and deadline intent has no date ordering. Filter dynamically and combine relevance/profile/deadline intent.
- **A20 Medium — misleading metrics/sample endpoints.** Health counts cached records as verified; sample endpoint claims 99.9% accuracy; settings call cache-only refreshes up to date. Label provenance and count actual fresh proofs.
- **A21 High — legacy calendars invent deadlines.** Missing/invalid dates become today + 14 days, and text is not escaped/folded. Use the shared RFC 5545 service and return 409 for unknown deadlines.
- **A22 High — public Telegram sending.** Anyone can target arbitrary chats; missing configuration returns simulated delivery success. Require account-scoped recipients and explicit preview semantics; do not send notifications during this audit.
- **A23 High — unsafe production configuration.** Wildcard credentialed CORS, public diagnostics/data paths, no production-secret guard, root Docker user and missing Docker exclusions. Fail safely and minimize public diagnostics and image contents.
- **A24 High — runtime/student artifacts tracked.** SQLite/WAL/SHM, Python cache files and 4,614 installed dependency files are tracked; `.gitignore` only covers one env path. Back up and untrack runtime artifacts while preserving local files; ignore secrets/uploads/caches comprehensively.
- **A25 High — stale dependency pin.** `python-multipart==0.0.6` precedes the official DoS fix in 0.0.18. Require a patched supported release and align both Python requirement entry points.
- **A26 High — deployment entry points invalid.** `app.py` executes missing `streamlit_app.py`; Render targets `master`, assumes app-root paths and combines free plan with a paid-only disk. Use FastAPI and repository-correct deployment roots/persistence instructions.
- **A27 Medium — unsupported claims in README/proof tooling.** README asserts 99.9% freshness/50ms and current live proof; proof script prints key fragments, fabricates wallet fallback and writes verification logs. Replace with bounded redacted diagnostics and measured evidence only.
- **A28 Medium — frontend eligibility/provenance drift.** UI duplicates gate checks, treats all old live timestamps alike and shows technical traces to students. Render backend eligibility/status and keep detailed diagnostics internal.
- **A29 Medium — data controls missing.** Settings provides appearance/auth controls but no personal-data export or resume removal. Add scoped reversible controls and verify persistence.
- **A30 Low — design token/effect inconsistency.** Existing cream/nav/accent differ from the new brief and decorative gradients/dots remain. Update tokens and reduce decoration without changing navigation/layout.

## Preservation

SQLite online backups were created outside Git in `%LOCALAPPDATA%/IRIS-one/backups/` before changes. Original desktop checkout and its independent uncommitted edits are untouched. Development occurs on `codex/hackathon-audit`, based on merged `main`.

Final dispositions and test evidence are recorded in `VALIDATION.md` after implementation.
