# IRIS onE — Student Opportunity Intelligence Platform

> **"Better opportunities. A brighter future."**  
> *Production-grade autonomous opportunity discovery, verification, and matching engine powered by TinyFish Web Agents and Gemini 2.5 Flash.*  

[![TinyFish Live Integration](https://img.shields.io/badge/TinyFish-Live%20Agent%20Verified-blue.svg)](https://tinyfish.ai)
[![Gemini 2.5 Flash](https://img.shields.io/badge/Gemini%202.5%20Flash-RAG%20Audited-purple.svg)](https://ai.google.dev/)


---

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

**IRIS onE** solves this through a **Two-Filter Autonomous Verification Engine**:
1. **Filter 1 (TinyFish Web Agents)**: Searches live portals (`api.search.tinyfish.ai`), renders JavaScript SPAs into clean Markdown with `ttl: 0` (`api.fetch.tinyfish.ai`), and deploys autonomous browser agents (`agent.tinyfish.ai/v1/automation/run`) to confirm whether the application button is active and accepting submissions.
2. **Filter 2 (Gemini 2.5 Flash + Policy Shield)**: Extracts normalized JSON, executes semantic matching against the student's academic tier and income bracket, and warns of exclusive grant conflicts.

---

## 🐟 How TinyFish Powers IRIS onE (Core Architecture)

IRIS onE natively integrates all three surfaces of the official **TinyFish Web Agent & Data Platform** to guarantee 99.9% data freshness and eliminate hallucinated student listings.
```mermaid

flowchart LR
    A["Student Query / Feed Request"] --> B["Stage A: TinySearch API<br/>(api.search.tinyfish.ai)"]
    B --> C["Stage B: TinyFetch API<br/>(api.fetch.tinyfish.ai, ttl: 0)"]
    C --> D["Stage C: TinyAgent Mako<br/>(agent.tinyfish.ai/v1/automation/run)"]
    D --> E["Filter Layer 2: Gemini 2.5 Flash<br/>(RAG + Policy Conflict Shield)"]
    E --> F["High-Concurrency SQLite WAL<br/>(Parse Once, Cache Globally)"]
    F --> G["Live Student Dashboard &<br/>RFC 5545 Calendar Feed (.ics)"]






glimse of the app

<img width="1358" height="741" alt="Screenshot 2026-10-19 165127" src="https://github.com/user-attachments/assets/75cf53a2-00b2-413c-a720-2a8f5f5397b9" />
<img width="1358" height="741" alt="Screenshot 2026-10-19 165127" src="https://github.com/user-attachments/assets/f77f8324-c82f-4c88-8883-6c64e73272f9" />
<img width="897" height="667" alt="Screenshot 2026-10-19 165443" src="https://github.com/user-attachments/assets/ae490a6b-c1cb-46d0-a391-34f2306f0bbc" />



<img width="502" height="477" alt="Screenshot 2026-10-20 015040" src="https://github.com/user-attachments/assets/48b60132-9485-4167-a548-dfff3adad230" />


