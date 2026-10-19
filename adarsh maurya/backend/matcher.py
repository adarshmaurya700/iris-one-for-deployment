"""
Opportunity matching engine for IRIS onE.

Scoring (clamped 65–99):
  +35 Academic tier & stream
  +25 State / domicile
  +25 Skill / interest overlap
  +15 Eligibility gate clearance
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set, Tuple


def _parse_csv_set(value: Optional[Any]) -> Set[str]:
    if value is None:
        return set()
    if isinstance(value, list):
        return {str(item).strip().lower() for item in value if str(item).strip()}
    return {item.strip().lower() for item in str(value).split(",") if item.strip()}


def _parse_json(value: Optional[Any]) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def _num(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace("%", "").replace("LPA", "").replace("lpa", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def parse_eligibility(opportunity: Dict[str, Any]) -> Dict[str, Any]:
    gates = _parse_json(opportunity.get("eligibility_json"))
    if not gates:
        gates = opportunity.get("eligibility_gates") or {}
    return gates or {}


def profile_from_user(user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    user = dict(user or {})
    skills = user.get("extracted_skills") or user.get("skills") or []
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]
    domains = user.get("recommended_domains") or user.get("domains") or []
    if isinstance(domains, str):
        domains = [s.strip() for s in domains.split(",") if s.strip()]
    return {
        "name": user.get("name") or "Adarsh Maurya",
        "academic_tier": user.get("academic_tier") or user.get("college") or "",
        "college": user.get("college") or "",
        "age": user.get("age") or 0,
        "state": user.get("state") or user.get("city") or "",
        "country": user.get("country") or "India",
        "cgpa_or_percentage": user.get("cgpa_or_percentage") or "",
        "family_income_lpa": _num(user.get("family_income_lpa")) if user.get("family_income_lpa") is not None else 6.0,
        "extracted_skills": skills,
        "skills": skills,
        "recommended_domains": domains,
        "domains": domains,
    }


def _academic_score(profile: Dict[str, Any], opp: Dict[str, Any], gates: Dict[str, Any]) -> Tuple[float, str]:
    blob = " ".join(
        [
            str(profile.get("academic_tier") or ""),
            str(profile.get("college") or ""),
        ]
    ).lower()
    tiers = gates.get("academic_tiers") or []
    if isinstance(tiers, str):
        tiers = [tiers]
    eligibility = str(opp.get("eligibility_criteria") or "").lower()
    tags = str(opp.get("tags") or "").lower()
    opp_type = str(opp.get("type") or "").lower()
    category = str(opp.get("category") or "").lower()

    school = any(k in blob for k in ["12th", "class 12", "cbse", "sose", "school"])
    ug_eng = any(k in blob for k in ["b.tech", "btech", "engineering", "usar", "ggsipu", "ug"])
    pg = any(k in blob for k in ["m.tech", "masters", "pg", "phd"])

    score = 12.0
    reason = "General academic eligibility"

    joined_tiers = " ".join(str(t).lower() for t in tiers)
    if school and any(k in joined_tiers or k in eligibility for k in ["12th", "class 11", "class 12", "school"]):
        score = 35.0
        reason = "School / Class 12 academic tier aligned"
    elif ug_eng and any(
        k in joined_tiers or k in eligibility or k in tags or k in category
        for k in ["ug", "engineering", "b.tech", "btech", "usar", "college"]
    ):
        score = 35.0
        reason = "UG Engineering academic tier aligned"
    elif pg and any(k in joined_tiers or k in eligibility for k in ["pg", "masters", "phd"]):
        score = 35.0
        reason = "Postgraduate academic tier aligned"
    elif not tiers and any(k in eligibility or k in tags or k in opp_type for k in ["student", "undergraduate", "scholarship", "hackathon", "free"]):
        score = 28.0
        reason = "Open student academic fit"
    elif blob:
        score = 18.0
        reason = f"Partial academic overlap ({profile.get('college') or profile.get('academic_tier')})"

    if ug_eng and "delhi" in (str(opp.get("title") or "") + eligibility).lower() and "usar" in blob:
        score = 35.0
        reason = "Matches GGSIPU USAR / Delhi state university enrollment"

    return min(35.0, score), reason


def _state_score(profile: Dict[str, Any], opp: Dict[str, Any], gates: Dict[str, Any]) -> Tuple[float, str]:
    user_state = str(profile.get("state") or "").strip().lower()
    allowed = gates.get("allowed_states") or []
    if isinstance(allowed, str):
        allowed = [allowed]
    allowed_l = [str(s).strip().lower() for s in allowed if str(s).strip()]
    location = str(opp.get("location") or opp.get("mode") or "").lower()
    open_locs = ["pan india", "all india", "online", "remote", "global", "international", "hybrid", "any"]

    if any(s in ("all", "all india", "pan india") for s in allowed_l) or any(loc in location for loc in open_locs):
        if user_state == "delhi" and (
            "delhi" in (opp.get("title") or "").lower()
            or "delhi" in allowed_l
            or "edistrict" in str(opp.get("source_portal") or "").lower()
        ):
            return 25.0, "Delhi domicile boost for NCT / e-District scheme"
        return 22.0, f"Open nationwide / {opp.get('location') or opp.get('mode') or 'PAN India'}"

    if user_state and (user_state in allowed_l or any(user_state in loc or loc in user_state for loc in allowed_l + [location])):
        return 25.0, f"State / domicile match: {profile.get('state')}"

    if not user_state:
        return 10.0, "State not set on profile"
    return 4.0, f"Outside listed states ({', '.join(allowed) if allowed else opp.get('location')})"


def _skill_score(profile: Dict[str, Any], opp: Dict[str, Any], gates: Dict[str, Any]) -> Tuple[float, str]:
    user_skills = _parse_csv_set(profile.get("extracted_skills")) | _parse_csv_set(profile.get("skills"))
    user_interests = _parse_csv_set(profile.get("recommended_domains")) | _parse_csv_set(profile.get("domains"))
    user_all = user_skills | user_interests

    req = _parse_csv_set(gates.get("required_skills_or_interests")) | _parse_csv_set(opp.get("required_skills"))
    tags = _parse_csv_set(opp.get("tags"))
    target = req | tags

    if not target:
        return 20.0, "No hard skill gate — open student perk"
    if not user_all:
        return 6.0, "No extracted skills yet"

    overlap = set()
    for skill in user_all:
        for t in target:
            if skill in t or t in skill:
                overlap.add(skill)
    if not overlap:
        return 8.0, "Limited semantic overlap with opportunity tags"

    ratio = len(overlap) / max(len(target), 1)
    pts = min(25.0, 10.0 + ratio * 20.0)
    return pts, f"Skill overlap: {', '.join(sorted(overlap)[:6])}"


def _gate_score(profile: Dict[str, Any], gates: Dict[str, Any]) -> Tuple[float, str]:
    marks_need = _num(gates.get("min_marks_percentage"))
    income_cap = _num(gates.get("max_family_income_lpa"))
    marks_have = _num(profile.get("cgpa_or_percentage"))
    income_have = _num(profile.get("family_income_lpa"))
    if income_have is None:
        income_have = 6.0

    pts = 0.0
    notes = []

    if marks_need is None:
        pts += 7.0
        notes.append("No minimum-marks gate")
    elif marks_have is None:
        pts += 5.0
        notes.append("Marks assumed eligible pending documents")
    elif marks_have >= marks_need:
        pts += 8.0
        notes.append(f"Clears {marks_need}% marks cutoff")
    else:
        pts += 1.0
        notes.append(f"Below {marks_need}% marks cutoff")

    if income_cap is None:
        pts += 7.0
        notes.append("No income cap")
    elif income_have <= income_cap:
        pts += 7.0
        notes.append(f"Income within ₹{income_cap} LPA cap")
    else:
        pts += 1.0
        notes.append(f"May exceed ₹{income_cap} LPA income cap")

    return min(15.0, pts), "; ".join(notes)


def _ai_reason(profile: Dict[str, Any], parts: List[str]) -> str:
    name_bits = []
    if profile.get("state"):
        name_bits.append(f"{profile['state']} domicile")
    if profile.get("college") or profile.get("academic_tier"):
        name_bits.append(profile.get("college") or profile.get("academic_tier"))
    skills = profile.get("extracted_skills") or profile.get("skills") or []
    if skills:
        name_bits.append(" and ".join([str(s) for s in list(skills)[:3]]) + " skills")
    if name_bits:
        return "Matches your " + ", ".join(name_bits[:-1] + ([name_bits[-1]] if len(name_bits) == 1 else ["and " + name_bits[-1]]))
    return "; ".join(parts)


def calculate_match(user: Optional[Dict[str, Any]], opportunity: Dict[str, Any]) -> Dict[str, Any]:
    profile = profile_from_user(user)
    gates = parse_eligibility(opportunity)

    academic_pts, academic_detail = _academic_score(profile, opportunity, gates)
    location_pts, loc_detail = _state_score(profile, opportunity, gates)
    skill_pts, skill_detail = _skill_score(profile, opportunity, gates)
    gate_pts, gate_detail = _gate_score(profile, gates)

    raw = academic_pts + location_pts + skill_pts + gate_pts
    overall = round(min(99.0, max(65.0, raw)), 1)

    reason = _ai_reason(profile, [academic_detail, loc_detail, skill_detail])

    breakdown = [
        {"factor": "Academic Tier", "weight": "35 pts", "score": round(academic_pts / 35.0 * 100.0, 1), "points": round(academic_pts, 1), "details": academic_detail},
        {"factor": "State / Domicile", "weight": "25 pts", "score": round(location_pts / 25.0 * 100.0, 1), "points": round(location_pts, 1), "details": loc_detail},
        {"factor": "Skill Match", "weight": "25 pts", "score": round(skill_pts / 25.0 * 100.0, 1), "points": round(skill_pts, 1), "details": skill_detail},
        {"factor": "Eligibility Gates", "weight": "15 pts", "score": round(gate_pts / 15.0 * 100.0, 1), "points": round(gate_pts, 1), "details": gate_detail},
    ]

    return {
        "overall": overall,
        "skill_match": round(skill_pts / 25.0 * 100.0, 1),
        "location_match": round(location_pts / 25.0 * 100.0, 1),
        "academic_match": round(academic_pts / 35.0 * 100.0, 1),
        "profile_completeness": round(gate_pts / 15.0 * 100.0, 1),
        "ai_match_reason": reason,
        "is_exclusive_tuition_grant": bool(gates.get("is_exclusive_tuition_grant")),
        "breakdown": breakdown,
    }


def detect_conflicts(opportunities: List[Dict[str, Any]], focus_id: Any = None) -> List[Dict[str, Any]]:
    exclusive = []
    for opp in opportunities:
        gates = parse_eligibility(opp)
        if gates.get("is_exclusive_tuition_grant"):
            exclusive.append(opp)
    if len(exclusive) < 2:
        return []

    warnings = []
    titles = [e.get("title") for e in exclusive]
    for opp in exclusive:
        if focus_id is not None and str(opp.get("id")) != str(focus_id) and str(opp.get("slug")) != str(focus_id):
            continue
        others = [t for t in titles if t != opp.get("title")]
        warnings.append(
            {
                "opportunity_id": opp.get("id"),
                "slug": opp.get("slug"),
                "warning": (
                    f"{opp.get('title')} is an exclusive tuition grant and cannot be claimed together with "
                    f"{', '.join(others)}. Stackable free perks (Gemini, Adobe, cloud credits) are unaffected."
                ),
            }
        )
    if not warnings:
        warnings.append(
            {
                "opportunity_id": exclusive[0].get("id"),
                "warning": (
                    "These tuition scholarships cannot be held simultaneously: " + " vs ".join(titles)
                ),
            }
        )
    return warnings


def score_catalog(
    user: Optional[Dict[str, Any]],
    opportunities: List[Dict[str, Any]],
    saved_ids: Optional[Set[Any]] = None,
) -> List[Dict[str, Any]]:
    saved_ids = saved_ids or set()
    saved_opps = [
        opp
        for opp in opportunities
        if opp.get("id") in saved_ids or str(opp.get("id")) in {str(s) for s in saved_ids} or opp.get("slug") in saved_ids
    ]
    conflicts = detect_conflicts(saved_opps) if len(saved_opps) >= 1 else detect_conflicts(
        [o for o in opportunities if parse_eligibility(o).get("is_exclusive_tuition_grant")]
    )
    conflict_by_id = {str(c.get("opportunity_id")): c.get("warning") for c in conflicts}
    conflict_by_slug = {str(c.get("slug")): c.get("warning") for c in conflicts if c.get("slug")}

    scored = []
    for opp in opportunities:
        item = dict(opp)
        match_info = calculate_match(user, item)
        item["match"] = match_info
        item["match_score"] = match_info["overall"]
        item["ai_match_reason"] = match_info.get("ai_match_reason")
        item["eligibility_gates"] = parse_eligibility(item)
        warning = conflict_by_id.get(str(item.get("id"))) or conflict_by_slug.get(str(item.get("slug")))
        if match_info.get("is_exclusive_tuition_grant") and len([o for o in saved_opps if parse_eligibility(o).get("is_exclusive_tuition_grant")]) >= 1:
            others = [o.get("title") for o in saved_opps if o.get("id") != item.get("id") and parse_eligibility(o).get("is_exclusive_tuition_grant")]
            if others:
                warning = warning or (
                    f"{item.get('title')} is an exclusive tuition grant and cannot be claimed together with {', '.join(others)}."
                )
        item["conflict_warning"] = warning
        scored.append(item)
    scored.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return scored


def eligibility_checklist(profile: Dict[str, Any], opportunity: Dict[str, Any]) -> List[Dict[str, Any]]:
    gates = parse_eligibility(opportunity)
    profile = profile_from_user(profile)
    items = []

    academic_pts, academic_detail = _academic_score(profile, opportunity, gates)
    items.append({"label": "Academic tier / stream", "pass": academic_pts >= 18, "detail": academic_detail})

    loc_pts, loc_detail = _state_score(profile, opportunity, gates)
    items.append({"label": "State / domicile", "pass": loc_pts >= 18, "detail": loc_detail})

    marks_need = _num(gates.get("min_marks_percentage"))
    marks_have = _num(profile.get("cgpa_or_percentage"))
    if marks_need is not None:
        items.append(
            {
                "label": f"Minimum marks ({marks_need}%)",
                "pass": marks_have is None or marks_have >= marks_need,
                "detail": f"Profile: {profile.get('cgpa_or_percentage') or 'not stated'}",
            }
        )

    income_cap = _num(gates.get("max_family_income_lpa"))
    income_have = _num(profile.get("family_income_lpa"))
    if income_cap is not None:
        items.append(
            {
                "label": f"Family income ≤ ₹{income_cap} LPA",
                "pass": income_have is None or income_have <= income_cap,
                "detail": f"Profile: {income_have if income_have is not None else 'assumed eligible'} LPA",
            }
        )

    docs = gates.get("mandatory_documents") or []
    if docs:
        items.append(
            {
                "label": "Mandatory documents",
                "pass": True,
                "detail": ", ".join(docs) if isinstance(docs, list) else str(docs),
            }
        )
    return items
