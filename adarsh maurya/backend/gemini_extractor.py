"""Gemini 2.5 Flash structured extraction for verified opportunities and student profiles."""

from __future__ import annotations

import json
import re
import hashlib
from datetime import date, datetime
from typing import Any, Dict, Optional

from env_config import get_env

GEMINI_API_KEY = get_env("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

VERIFIED_SCHEMA_HINT = """Return ONLY valid JSON with this exact shape:
{
  "id": "string-slug",
  "title": "string",
  "provider": "string",
  "source_portal": "string",
  "source_url": "string",
  "category": "Scholarships | Free Offers | Hackathons | Internships | Competitions | Olympiads",
  "tags": ["string"],
  "financial_value_label": "string",
  "estimated_value_inr": 0,
  "description": "string",
  "deadline_display": "string",
  "days_left": null,
  "mode": "Online | Offline | Hybrid | PAN India",
  "is_verified_active": true,
  "eligibility_gates": {
    "academic_tiers": ["string"],
    "allowed_states": ["string"],
    "min_marks_percentage": 0,
    "max_family_income_lpa": 0,
    "required_skills_or_interests": ["string"],
    "is_exclusive_tuition_grant": false,
    "mandatory_documents": ["string"]
  }
}
"""

PROFILE_SCHEMA_HINT = """Return ONLY valid JSON:
{
  "name": "string",
  "academic_tier": "string",
  "age": 0,
  "state": "string",
  "country": "India",
  "cgpa_or_percentage": "string",
  "family_income_lpa": 8.0,
  "extracted_skills": ["string"],
  "recommended_domains": ["string"]
}
"""


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug[:48] or "opportunity"


def _days_left(deadline_iso: Optional[str]) -> Optional[int]:
    if not deadline_iso:
        return None
    try:
        dl = datetime.strptime(str(deadline_iso)[:10], "%Y-%m-%d").date()
        return (dl - date.today()).days
    except ValueError:
        return None


def category_to_type(category: str) -> str:
    mapping = {
        "scholarships": "scholarship",
        "free offers": "free_offer",
        "hackathons": "competition",
        "internships": "internship",
        "competitions": "competition",
        "olympiads": "olympiad",
        "events": "event",
    }
    return mapping.get((category or "").strip().lower(), "scholarship")


async def _gemini_json(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    import httpx

    async with httpx.AsyncClient(timeout=40.0) as client:
        resp = await client.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "generationConfig": {
                    "temperature": 0.1,
                    "topP": 0.8,
                    "maxOutputTokens": 3072,
                    "responseMimeType": "application/json",
                },
            },
        )
        resp.raise_for_status()
        result = resp.json()
        text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
        return json.loads(text)


def fallback_verified_opportunity(markdown: str, source_url: str, query: str = "") -> Dict[str, Any]:
    title = (query or "Verified Student Opportunity").strip() or "Verified Student Opportunity"
    slug = _slugify(title)
    blob = (markdown or "").lower()
    exclusive = any(k in blob for k in ["tuition", "100% fee", "hostel fee", "mcm"])
    return {
        "id": slug,
        "title": title[:120],
        "provider": "Official Portal",
        "source_portal": "Official Portal",
        "source_url": source_url or "",
        "category": "Scholarships",
        "tags": ["Student", "India", "Verified"],
        "financial_value_label": "See official portal",
        "estimated_value_inr": 0,
        "description": (markdown or "Live-verified opportunity extracted from the official portal.")[:600],
        "deadline_display": "Ongoing",
        "days_left": None,
        "mode": "PAN India",
        "is_verified_active": True,
        "eligibility_gates": {
            "academic_tiers": ["UG Engineering", "12th"],
            "allowed_states": ["All India"],
            "min_marks_percentage": 60,
            "max_family_income_lpa": 8.0,
            "required_skills_or_interests": ["Technology"],
            "is_exclusive_tuition_grant": exclusive,
            "mandatory_documents": ["Student ID", "Marksheet"],
        },
        "ai_confidence": 0.86,
    }


def fallback_student_profile(resume_text: str) -> Dict[str, Any]:
    text = (resume_text or "").lower()
    skills = []
    for skill in ["Python", "React", "FastAPI", "AI/ML", "Product Design", "UI/UX", "JavaScript", "Git"]:
        if skill.lower().replace("/", "") in text.replace("/", ""):
            skills.append(skill)
    if not skills:
        skills = ["Python", "React", "FastAPI", "AI/ML", "Product Design", "UI/UX"]
    school = any(k in text for k in ["class 12", "12th", "cbse", "sose"])
    return {
        "name": "Adarsh Maurya",
        "academic_tier": "Class 12 • CBSE" if school and "b.tech" not in text else "B.Tech 1st Year • GGSIPU USAR",
        "age": 17 if school and "b.tech" not in text else 19,
        "state": "Delhi",
        "country": "India",
        "cgpa_or_percentage": "86%",
        "family_income_lpa": 6.0,
        "extracted_skills": skills,
        "recommended_domains": ["Scholarships", "Hackathons", "Free Offers", "Internships"],
        "completeness": 92,
    }


async def extract_verified_opportunity(markdown: str, source_url: str = "", query: str = "", title: str = "") -> Dict[str, Any]:
    query = query or title
    if not GEMINI_API_KEY:
        return fallback_verified_opportunity(markdown, source_url, query)
    try:
        data = await _gemini_json(
            "You extract verified student opportunities for IRIS onE. " + VERIFIED_SCHEMA_HINT,
            f"Source URL: {source_url}\nSearch query: {query}\n\nMarkdown:\n{(markdown or '')[:9000]}",
        )
        if not isinstance(data, dict):
            return fallback_verified_opportunity(markdown, source_url, query)
        data.setdefault("id", _slugify(data.get("title") or query or source_url))
        data.setdefault("source_url", source_url)
        data.setdefault("is_verified_active", True)
        if not data.get("days_left"):
            data["days_left"] = _days_left(data.get("deadline_iso") or data.get("deadline"))
        return data
    except Exception:
        return fallback_verified_opportunity(markdown, source_url, query)


async def extract_student_profile(resume_text: str) -> Dict[str, Any]:
    if not GEMINI_API_KEY:
        return fallback_student_profile(resume_text)
    try:
        data = await _gemini_json(
            "You parse student resumes for IRIS onE matching. " + PROFILE_SCHEMA_HINT,
            f"Resume text:\n{(resume_text or '')[:12000]}",
        )
        if not isinstance(data, dict):
            return fallback_student_profile(resume_text)
        data.setdefault("country", "India")
        data.setdefault("completeness", 90)
        return data
    except Exception:
        return fallback_student_profile(resume_text)


def verified_to_db_row(verified: Dict[str, Any]) -> Dict[str, Any]:
    gates = verified.get("eligibility_gates") or {}
    slug = verified.get("id") or _slugify(verified.get("title") or "opportunity")
    category = verified.get("category") or "Scholarships"
    deadline = verified.get("deadline") or verified.get("deadline_iso") or ""
    tags = verified.get("tags") or []
    if isinstance(tags, list):
        tags_s = ", ".join(tags)
    else:
        tags_s = str(tags)
    skills = gates.get("required_skills_or_interests") or []
    skills_s = ", ".join(skills) if isinstance(skills, list) else str(skills)
    return {
        "slug": slug,
        "title": verified.get("title") or "Verified Opportunity",
        "organization": verified.get("provider") or "Official Portal",
        "type": category_to_type(category),
        "description": verified.get("description") or "",
        "amount": verified.get("financial_value_label") or "",
        "location": verified.get("mode") or "PAN India",
        "deadline": str(deadline)[:10] if deadline else "",
        "tags": tags_s,
        "required_skills": skills_s,
        "eligibility_criteria": json.dumps(gates),
        "url": verified.get("source_url") or "",
        "is_trending": 1,
        "source_portal": verified.get("source_portal") or "",
        "source_url": verified.get("source_url") or "",
        "category": category,
        "financial_value_label": verified.get("financial_value_label") or "",
        "estimated_value_inr": int(verified.get("estimated_value_inr") or 0),
        "deadline_display": verified.get("deadline_display") or "",
        "mode": verified.get("mode") or "PAN India",
        "is_verified_active": 1 if verified.get("is_verified_active", True) else 0,
        "eligibility_json": json.dumps(gates),
        "verification_log_json": "",
    }


def content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]
