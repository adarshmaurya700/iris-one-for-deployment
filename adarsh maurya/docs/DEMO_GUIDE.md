# IRIS onE hackathon demonstration

Motto: **Better Opportunities. A Brighter You.**

## Before presenting

Start explicit demo mode using `DEPLOYMENT.md`. Keep the mode label visible. Use a text-based resume containing details you are comfortable showing. Local records, scoring, checklists, calendar exports and deterministic Ask IRIS need no external key or venue Wi-Fi.

For live verification, use a separate live database, configure valid credentials, and run the bounded diagnostic beforehand. At audit time Gemini was missing and the TinyFish credential returned HTTP 401. Until corrected, demonstrate the honest unconfirmed result and describe external verification as **not live-validated**.

## Walkthrough

1. **Identify the mode.** Explain that demo records/profile are examples and external calls are disabled. Open Home and show counts from this workspace.
2. **Authenticate.** Create an account and sign out/in. A new account does not inherit the sample shortlist. Accounts use bcrypt/JWT; guests use separate signed HttpOnly cookies.
3. **Onboard.** Complete personal/education details, graduation year and skills. Optional marks, income and NIRF confirmation can be unknown. Continue to step two, select interests, and save.
4. **Upload a resume.** Upload TXT, DOCX or a text-based PDF. Show skill tags and completeness updating, then refresh. Without Gemini, the deterministic parser only extracts supported facts and does not invent age, income or institution.
5. **Explore.** Search, filter categories/location/deadline, change sorting, and try Ctrl+K / Cmd+K. Reference fixtures remain visibly unverified and past deadlines are excluded from the current feed.
6. **Explain a match.** Open a detail. Academic compatibility contributes 35, domicile 25, skills 25 and conditions 15. This is compatibility, **not winning probability**. Show unknown vs failed vs confirmed conditions. Official program rules remain authoritative.
7. **Explain verification.** Click Verify now. Demo mode reports no live verification and preserves cached data. Configured live mode discovers a source, reads it, inspects an actual application action without submission, and validates extraction. Success earns a recent badge that expires after 12 hours. Closed, expired and blocked sources do not earn live badges.
8. **Save and track.** Save a record, refresh, and open Saved. Open Apply, inspect official channels, check documents and track the application. Change Draft → Applied → Under Review → Interview and refresh to prove persistence.
9. **Ask IRIS.** Ask “Which scholarships match my profile?”, “Why this match?”, “What documents do I need for Airtel?” and “Can Airtel and Delhi MCM cover the same tuition?”. Answers use the scoped profile/catalog and source mini-cards. Named historical records can be explained while marked expired. Tuition conflicts are cached policy guidance, not evidence of an accepted award.
10. **Manage deadlines.** Navigate calendar months, including June 2025, then return to today. Download `.ics` for a tracked record with a stored deadline and show 72/24-hour reminders. Unknown dates disable export or return 409; no date is invented.
11. **Show data ownership.** Change a preference, refresh, and export the workspace JSON. Remove a stored resume while retaining profile edits. Provider configuration is separate from proof of a successful live check.
12. **Show internal diagnostics.** Use `/api/admin/diagnostics`, supplying the admin header securely in production. Explain LIVE_SUCCESS, LIVE_FAILED, CACHED_RESULT, LOCAL_FALLBACK and NOT_CONFIGURED. Do not project credentials or raw private documents.

## Q&A

- **Answer sources:** local keyword/vector retrieval and profile compatibility, with Gemini → Groq → Ollama → identified local fallback. Pasting a URL into chat does not secretly launch a web agent.
- **Do unit tests prove providers work?** No. Mocked contracts/failures are separate from controlled real calls and verification evidence. Current external limits are in `VALIDATION.md`.
- **Data storage:** scoped profiles, parsed resume text/metadata, saves, application statuses/checklists, catalog and actual sync history. Normal profile responses and cloud assistant context exclude raw resume text. Configured Gemini resume extraction can receive the supplied resume text; use consented demo documents.
- **Failure handling:** preserve data, expose unconfirmed/previous verification, keep eligibility unknown when facts are missing, and show failed writes instead of fake success.
- **Persistence:** SQLite WAL on persistent storage or configured PostgreSQL/pgvector. An ephemeral filesystem cannot preserve a real student demo across restarts.
- **Performance:** no production latency or scalability guarantee is claimed. Larger catalogs and multiple replicas need benchmarking and a shared rate limiter.
