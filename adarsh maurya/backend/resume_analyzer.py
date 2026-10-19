"""Extract text from PDF/DOCX/TXT resumes and structure a StudentProfile."""

from __future__ import annotations

import io
import json
import os
import sqlite3
from typing import Any, Dict, Optional

from gemini_extractor import extract_student_profile as gemini_extract_profile, fallback_student_profile

SAMPLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_resume.txt")
SAMPLE_PROFILE = fallback_student_profile("")


def load_sample_resume_text() -> str:
    if os.path.isfile(SAMPLE_PATH):
        with open(SAMPLE_PATH, "r", encoding="utf-8") as handle:
            return handle.read()
    return "Adarsh Maurya\nB.Tech CSE 1st Year GGSIPU USAR Delhi\nPython React FastAPI AI/ML"


def extract_text_from_bytes(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".txt") or name.endswith(".md"):
        return data.decode("utf-8", errors="ignore")
    if name.endswith(".docx"):
        try:
            import docx

            document = docx.Document(io.BytesIO(data))
            return "\n".join(p.text for p in document.paragraphs)
        except Exception:
            return data.decode("utf-8", errors="ignore")
    if name.endswith(".pdf") or not name:
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            pages = []
            for page in reader.pages:
                pages.append(page.extract_text() or "")
            return "\n".join(pages)
        except Exception:
            return data.decode("utf-8", errors="ignore")
    return data.decode("utf-8", errors="ignore")


def _normalize_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    skills = profile.get("extracted_skills") or profile.get("skills") or []
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]
    domains = profile.get("recommended_domains") or profile.get("domains") or []
    if isinstance(domains, str):
        domains = [s.strip() for s in domains.split(",") if s.strip()]
    college = profile.get("academic_tier") or profile.get("college") or "B.Tech 1st Year • GGSIPU USAR"
    school = any(k in college for k in ["12th", "Class 12", "CBSE", "SOSE"])
    profile["extracted_skills"] = skills
    profile["skills"] = skills
    profile["recommended_domains"] = domains
    profile["domains"] = domains
    profile["college"] = college
    profile["academic_tier"] = college
    profile["displayClass"] = "SOSE Kalkaji" if school else "USAR"
    profile["university"] = "SOSE Kalkaji" if school else "USAR"
    profile["city"] = profile.get("state") or "Delhi"
    profile["country"] = profile.get("country") or "India"
    profile["completeness"] = int(profile.get("completeness") or 92)
    return profile


async def extract_student_profile(resume_text: str) -> Dict[str, Any]:
    profile = await gemini_extract_profile(resume_text)
    return _normalize_profile(profile)


async def analyze_resume_bytes(filename: str, data: Optional[bytes], raw_text: Optional[str] = None) -> dict:
    if raw_text:
        text = raw_text
    elif data:
        text = extract_text_from_bytes(filename, data)
    else:
        text = load_sample_resume_text()
    profile = await extract_student_profile(text)
    profile["resume_filename"] = filename or "sample_resume.txt"
    profile["resume_chars"] = len(text or "")
    return profile


def persist_profile_to_user(db: sqlite3.Connection, user_id: int, profile: Dict[str, Any]) -> Dict[str, Any]:
    skills = profile.get("extracted_skills") or []
    skills_s = ", ".join(skills) if isinstance(skills, list) else str(skills)
    domains = profile.get("recommended_domains") or []
    domains_s = ", ".join(domains) if isinstance(domains, list) else str(domains)
    cursor = db.cursor()
    cursor.execute(
        """
        UPDATE users SET
            name = COALESCE(NULLIF(?, ''), name),
            college = ?,
            age = COALESCE(?, age),
            state = COALESCE(NULLIF(?, ''), state),
            country = COALESCE(NULLIF(?, ''), country),
            skills = ?,
            domains = ?,
            academic_tier = ?,
            cgpa_or_percentage = ?,
            family_income_lpa = ?,
            extracted_skills = ?,
            recommended_domains = ?,
            profile_json = ?
        WHERE id = ?
        """,
        (
            profile.get("name") or "",
            profile.get("college") or profile.get("academic_tier") or "",
            profile.get("age") or 0,
            profile.get("state") or "",
            profile.get("country") or "India",
            skills_s,
            domains_s,
            profile.get("academic_tier") or "",
            str(profile.get("cgpa_or_percentage") or ""),
            profile.get("family_income_lpa") or 8.0,
            skills_s,
            domains_s,
            json.dumps(profile),
            user_id,
        ),
    )
    db.commit()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    user = dict(row) if row else dict(profile)
    user.pop("password_hash", None)
    return user
