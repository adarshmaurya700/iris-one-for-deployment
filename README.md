IRIS onE

One dashboard for verified student scholarships, hackathons, and free developer perks.

Instead of checking 15 different websites every week, students upload their resume once to see verified opportunities they actually qualify for—with live link checks and 1-click calendar reminders.

What It Does

Unifies Scattered Portals: Brings scholarships, hackathons, internships, and student software packs (from Unstop, Devfolio, Buddy4Study, and state portals) into one clean feed.

Verifies Links Live: TinyFish web agents (TinySearch, TinyFetch, and Mako) visit each page to confirm the "Apply" button is active, and Gemini 2.5 Flash extracts deadlines, stipend amounts, and eligibility rules into JSON.

Matches Your Resume: Parses PDF/DOCX resumes and ranks opportunities in under 50ms based on Academic Tier, State Domicile, Skills, and Income/Marks cutoffs.

Flags Tuition Conflicts: Warns students when two full-tuition waivers legally conflict (e.g., Bharti Airtel Grant vs. Delhi MCM), while marking developer tools (Gemini Pro, GitHub Pack) as stackable.

Syncs Deadlines (.ics): 1-click calendar export with 72-hour and 24-hour reminders.

How It Works ("Parse Once, Cache Globally")

Background workers crawl and verify listings once every 12 hours so student searches run locally against SQLite in under 50ms with zero live LLM token cost per view.

Portals ──► TinyFish (Search + Fetch + Mako Agent) ──► Gemini 2.5 Flash (JSON) ──► SQLite Cache ──► FastAPI UI


(Live TinyFish Mako Agent verification logs are saved in backend/tinyfish_live_proof.json.)

Tech Stack

Backend: Python 3.10+, FastAPI, SQLite (WAL mode)

Web Agents & AI: TinyFish API (Search, Fetch, Mako Agent), Google Gemini 2.5 Flash

Frontend: Vanilla JS SPA, HTML5, Tailwind CSS

Parsing & Export: pypdf, python-docx, RFC 5545 (.ics)
