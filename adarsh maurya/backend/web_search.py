"""
Live web search for hackathons & scholarships.
Uses TinyFish Search only (no Fetch/Agent, so no per-run wallet spend).
"""
from __future__ import annotations

import re
import time
from typing import Dict, List, Optional
from urllib.parse import urlparse

from tinyfish_pipeline import _call_tinyfish_search, _has_tinyfish_key

CACHE_TTL_SECONDS = 6 * 60 * 60
_CACHE: Dict[str, tuple[float, Dict]] = {}

MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]
TYPO_FIXES = {"hackthon": "hackathon", "hackthons": "hackathons", "scholarshp": "scholarship"}

RELEVANT_RE = re.compile(
    r"hackathon|hackathons|hack|scholarship|grant|fellowship|competition|internship|challenge",
    re.IGNORECASE,
)


def _normalize_query(user_q: str) -> str:
    q = user_q.strip().lower()
    for wrong, right in TYPO_FIXES.items():
        q = q.replace(wrong, right)
    return re.sub(r"\s+", " ", q)


def _build_search_query(user_q: str) -> str:
    q = _normalize_query(user_q)
    parts = [q, "India student"]

    if "hack" in q:
        parts.append("hackathon registration")
    if "scholarship" in q:
        parts.append("scholarship application")
    if "hack" not in q and "scholarship" not in q:
        parts.append("hackathon OR scholarship")

    month = next((m for m in MONTHS if m in q), None)
    if month:
        parts.append(f"{month.title()} 2026")
    else:
        parts.append("2026")

    return " ".join(parts)


def _type_for(text: str) -> str:
    t = text.lower()
    if "hack" in t:
        return "Hackathon"
    if "scholarship" in t or "grant" in t or "fellowship" in t:
        return "Scholarship"
    if "internship" in t:
        return "Internship"
    return "Competition"


def _normalize_item(item: Dict) -> Optional[Dict]:
    url = (item.get("url") or item.get("link") or "").strip()
    title = (item.get("title") or "").strip()
    snippet = (item.get("snippet") or item.get("description") or "").strip()
    if not url or not title:
        return None

    text = f"{title} {snippet}"
    if not RELEVANT_RE.search(text):
        return None

    domain = urlparse(url).netloc.replace("www.", "")
    return {
        "id": f"web-{abs(hash(url))}",
        "title": title,
        "provider": domain,
        "url": url,
        "snippet": snippet[:220],
        "type": _type_for(text),
        "source": "live_web",
    }


def _dedupe(items: List[Dict]) -> List[Dict]:
    seen, out = set(), []
    for it in items:
        key = (it["provider"], it["title"].lower()[:60])
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out


async def search_web_opportunities(user_q: str, limit: int = 8) -> Dict:
    cache_key = _normalize_query(user_q)
    cached = _CACHE.get(cache_key)
    if cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
        return {**cached[1], "cached": True}

    if not _has_tinyfish_key():
        return {"results": [], "mode": "demo", "query": user_q, "cached": False}

    search_q = _build_search_query(user_q)
    raw = await _call_tinyfish_search(
        search_q,
        purpose="Find current student hackathon and scholarship registration pages in India",
    )

    items = raw.get("results") or raw.get("data") or []
    normalized = [_normalize_item(i) for i in items if isinstance(i, dict)]
    results = _dedupe([i for i in normalized if i])[:limit]

    payload = {"results": results, "mode": "live", "query": search_q, "cached": False}
    _CACHE[cache_key] = (time.time(), payload)
    return payload