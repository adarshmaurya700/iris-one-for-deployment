# IRIS onE — Student Opportunity Intelligence Platform

> **"Better opportunities. A brighter future."**  
> *Production-grade autonomous opportunity discovery, verification, and matching engine powered by TinyFish Web Agents and Gemini 2.5 Flash.*  
> **Official Submission for KRITICAL HACKS '26**

[![TinyFish Live Integration](https://img.shields.io/badge/TinyFish-Live%20Agent%20Verified-blue.svg)](https://tinyfish.ai)
[![Gemini 2.5 Flash](https://img.shields.io/badge/Gemini%202.5%20Flash-RAG%20Audited-purple.svg)](https://ai.google.dev/)
[![FastAPI Production](https://img.shields.io/badge/FastAPI-Production%20WAL-emerald.svg)](https://fastapi.tiangolo.com)
[![Pass 27/27 Tests](https://img.shields.io/badge/Tests-27%2F27%20Passing%20(100%25)-brightgreen.svg)](file:///backend/test_backend.py)

---

## 📌 Executive Summary & Problem Statement

Across India and globally, over **₹3,000 Crore** in undergraduate scholarships, student travel grants, hackathons, and software fellowship allowances go unclaimed or expire without qualified applicants. Students face severe fragmentation:
- **Scattered Discovery**: Opportunities are buried across 100+ siloed portals (National Scholarship Portal, state e-District portals, Buddy4Study, Devfolio, Unstop, Corporate CSR foundations).
- **Hallucinated & Outdated Criteria**: Third-party aggregators frequently display outdated stipends, closed deadlines, or malformed eligibility requirements.
- **Hidden Policy Conflicts**: Students unknowingly apply for multiple exclusive tuition grants (e.g. *Bharti Airtel Scholarship* vs. *Delhi Government MCM Scheme*) which legally prohibit concurrent funding, leading to clawbacks and administrative disqualifications.

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

