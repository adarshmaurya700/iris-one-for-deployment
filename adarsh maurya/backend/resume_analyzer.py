"""Extract text from PDF/DOCX/TXT resumes and structure a StudentProfile."""

from __future__ import annotations

import io
import json
import os
import sqlite3
from typing import Any, Dict, Optional

from gemini_extractor import extract_student_profile as gemini_extract_profile, fallback_student_profile

SAMPLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_resume.txt")
SAMPLE_PROFILE = {"is_simulated": True}


def load_sample_resume_text() -> str:
    if os.path.isfile(SAMPLE_PATH):
        with open(SAMPLE_PATH, "r", encoding="utf-8") as handle:
            return handle.read()
    return "Adarsh Maurya\nB.Tech CSE 1st Year GGSIPU USAR Delhi\nPython React FastAPI AI/ML"


def extract_text_from_bytes(filename, data):
    from fastapi import HTTPException
    from zipfile import ZipFile, BadZipFile
    name = (filename or '').lower()
    try:
        if name.endswith('.txt'):
            text = data.decode('utf-8-sig')
            if '\x00' in text:
                raise ValueError('Binary content in a text file.')
            return text[:100000]
        if name.endswith('.docx'):
            import docx
            with ZipFile(io.BytesIO(data)) as archive:
                if sum(item.file_size for item in archive.infolist()) > 20 * 1024 * 1024 or len(archive.infolist()) > 500:
                    raise ValueError('Compressed document exceeds the extraction limit.')
            document = docx.Document(io.BytesIO(data))
            return '\n'.join(p.text for p in document.paragraphs)[:100000]
        if name.endswith('.pdf') and data.startswith(b'%PDF-'):
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted or len(reader.pages) > 40:
                raise ValueError('Encrypted PDFs or PDFs longer than 40 pages are unsupported.')
            return '\n'.join(page.extract_text() or '' for page in reader.pages)[:100000]
        raise ValueError('The document does not match its file type.')
    except Exception:
        raise HTTPException(400, 'This document could not be read. Upload a valid text-based PDF, DOCX or UTF-8 TXT resume.') from None


def _normalize_profile(profile):
    skills = profile.get('extracted_skills') or []
    profile['skills'] = skills
    profile['domains'] = profile.get('recommended_domains') or []
    profile['college'] = profile.get('academic_tier') or ''
    profile['university'] = profile.get('institution') or ''
    profile['city'] = profile.get('state') or ''
    return profile


async def extract_student_profile(resume_text: str) -> Dict[str, Any]:
    profile = await gemini_extract_profile(resume_text)
    return _normalize_profile(profile)


async def analyze_resume_bytes(filename: str, data: Optional[bytes], raw_text: Optional[str] = None) -> dict:
    if raw_text:
        text = raw_text
    elif data:
        import asyncio
        text = await asyncio.to_thread(extract_text_from_bytes, filename, data)
    else:
        from fastapi import HTTPException
        raise HTTPException(400, 'Choose a resume or explicitly request the demo sample.')
    if not text or len(text.strip()) < 10:
        from fastapi import HTTPException
        raise HTTPException(400, 'No readable resume text was found. Use a text-based document.')
    profile = await extract_student_profile(text)
    profile["resume_filename"] = filename or "sample_resume.txt"
    profile["resume_chars"] = len(text or "")
    return profile


def persist_profile_to_user(db: sqlite3.Connection, user_id: int, profile: Dict[str, Any]) -> Dict[str, Any]:
    skills = profile.get("extracted_skills") or []
    skills_s = ", ".join(skills) if isinstance(skills, list) else str(skills)
    domains = profile.get("recommended_domains") or []
    domains_s = ", ".join(domains) if isinstance(domains, list) else str(domains)
    mapping = {'name': 'name', 'college': 'college', 'age': 'age', 'state': 'state', 'country': 'country', 'academic_tier': 'academic_tier', 'cgpa_or_percentage': 'cgpa_or_percentage', 'family_income_lpa': 'family_income_lpa'}
    updates = {target: profile[key] for key,target in mapping.items() if profile.get(key) not in (None, '')}
    updates.update(skills=skills_s, extracted_skills=skills_s, profile_json=json.dumps({key:value for key,value in profile.items() if key != 'user'}))
    db.execute('UPDATE users SET ' + ', '.join(f'{key} = ?' for key in updates) + ' WHERE id = ?', tuple(updates.values()) + (user_id,))
    db.commit()
    user = dict(db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone())
    user.pop('password_hash', None)
    return user
