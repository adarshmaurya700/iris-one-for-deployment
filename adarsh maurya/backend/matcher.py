"""One transparent 35/25/25/15 compatibility score, never a selection probability."""
from __future__ import annotations
import hashlib
import json
import math
import re
from typing import Any, Dict, List, Optional, Set
from catalog import json_value, today_in_india


def _num(value):
    try:
        number = float(str(value).strip().rstrip('%'))
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def parse_eligibility(opp):
    value = json_value(opp.get('eligibility_json') or opp.get('eligibility_gates') or opp.get('eligibility_criteria'), {})
    return value if isinstance(value, dict) else {}


def _skills(value):
    if isinstance(value, str):
        value = json_value(value) if value.startswith('[') else value.split(',')
    return {str(s).strip().lower() for s in (value or []) if str(s).strip()} - {'any', 'all', 'none'}


def profile_from_user(user):
    user = dict(user or {})
    income = _num(user.get('family_income_inr'))
    if income is None and user.get('family_income_lpa') is not None:
        parsed = _num(user['family_income_lpa']); income = parsed * 100000 if parsed is not None else None
    stage = str(user.get('academic_stage') or user.get('college') or user.get('academic_tier') or '')
    return {**user, 'academic_stage': stage, 'state_domicile': user.get('state_domicile') or user.get('state') or '',
            'class_12_pct': _num(user.get('class_12_pct') if user.get('class_12_pct') is not None else user.get('cgpa_or_percentage')),
            'family_income_inr': income, 'skills_json': list(_skills(user.get('skills_json') or user.get('extracted_skills') or user.get('skills')))}


def evaluate_match_and_conflicts(student, opp, tracked_exclusive_titles):
    student = profile_from_user(student)
    rules = parse_eligibility(opp)
    checks = []
    def check(label, passed, detail):
        checks.append({'label': label, 'pass': passed, 'status': 'confirmed' if passed is True else 'failed' if passed is False else 'unknown', 'detail': detail})
        return passed
    stage = student['academic_stage'].lower()
    school = any(w in stage for w in ('school', 'class ', '12th', '11th', 'tier_1'))
    tier = ('TIER_1_SCHOOL' if school else 'TIER_2_UG_PG') if stage else ''
    target = opp.get('academic_tier') or ''
    expected = rules.get('academic_tiers') or []
    expected = [expected] if isinstance(expected, str) else expected
    academic_pass = None
    if tier and (target or expected):
        academic_pass = target in ('ALL', tier)
        if expected:
            text = ' '.join(expected).lower()
            school_allowed = any(w in text for w in ('school', '12th', 'class '))
            ug_allowed = any(w in text for w in ('ug', 'undergraduate', 'engineering', 'college', 'b.tech'))
            pg_allowed = any(w in text for w in ('pg', 'masters', 'postgraduate', 'phd'))
            if school:
                academic_pass = school_allowed or 'any student' in text
            elif 'engineering' in text and not school_allowed and not pg_allowed:
                academic_pass = True if any(w in stage for w in ('b.tech', 'btech', 'engineering', 'b.e.', 'usar')) else None
            elif ug_allowed or pg_allowed:
                academic_pass = True
    academic = 35 if academic_pass is True else 0
    check('Academic compatibility', academic_pass, 'Academic stage matches the recorded criteria.' if academic_pass else 'Confirm the required academic stage and stream.' if academic_pass is None else 'Academic stage does not match the recorded criteria.')
    state = student['state_domicile'].strip().lower()
    states = rules.get('allowed_states') or opp.get('location_state') or []
    states = [s.strip() for s in states.split(',')] if isinstance(states, str) else states
    states = [s.lower() for s in states]
    unrestricted = any(s in ('all', 'all india', 'pan india', 'national', 'global', 'international', 'online', 'any') for s in states)
    domicile_pass = True if unrestricted else state in states if state and states else None
    domicile = 25 if domicile_pass else 0
    check('State / domicile', domicile_pass, 'No state restriction is recorded.' if unrestricted else 'Domicile matches the listed states.' if domicile_pass else 'Add your domicile or confirm the source requirement.' if domicile_pass is None else 'Domicile is outside the listed states.')
    required = _skills(opp.get('skills_tags_json') or opp.get('required_skills') or rules.get('required_skills_or_interests'))
    own = _skills(student.get('skills_json'))
    overlap = len(own & required) / len(required) if required else 1
    sv = compute_deterministic_embedding(' '.join(sorted(own)))
    ov = json_value(opp.get('embedding_json'))
    skills = round(25 * (0.6 * overlap + 0.4 * max(0, cosine_similarity(sv, ov))), 1) if required and own else 0 if required else 25
    gate_start = len(checks)
    minimum = _num(opp.get('min_marks_pct') if opp.get('min_marks_pct') else rules.get('min_marks_percentage'))
    if minimum:
        marks = student['class_12_pct']
        check('Minimum marks', marks >= minimum if marks is not None else None, f'Requires at least {minimum:g}% marks; profile: {str(marks) + "%" if marks is not None else "not provided"}.')
    cap = _num(opp.get('max_family_income_inr'))
    if cap is None and rules.get('max_family_income_lpa') is not None:
        cap = _num(rules['max_family_income_lpa']); cap = cap * 100000 if cap is not None else None
    if cap is not None and cap < 99999999:
        income = student['family_income_inr']
        check('Family income', income <= cap if income is not None else None, f'Requires family income no more than INR {cap:,.0f}; profile income is ' + ('provided.' if income is not None else 'not provided.'))
    if opp.get('nirf_top_50_required'):
        value = student.get('nirf_top_50')
        check('Institution ranking', bool(value) if value is not None else None, 'Requires confirmed admission in a top-50 NIRF engineering institution.')
    if rules.get('min_age') is not None:
        age = _num(student.get('age'))
        check('Minimum age', age >= rules['min_age'] if age is not None else None, f'Requires age {rules["min_age"]} or above.')
    conditions = checks[gate_start:]
    rules_known = bool(rules or minimum or (cap is not None and cap < 99999999))
    if not rules_known:
        check('Program conditions', None, 'No structured eligibility conditions are recorded; check the official rules.')
        conditions = checks[gate_start:]
    gates = round(15 * sum(item['pass'] is True for item in conditions) / len(conditions), 1) if conditions else 15
    expired = bool((opp.get('deadline_iso') or opp.get('deadline') or '') < today_in_india().isoformat()) if (opp.get('deadline_iso') or opp.get('deadline')) else False
    closed = expired or opp.get('verification_status') in ('CLOSED', 'EXPIRED', 'ARCHIVED')
    failed = any(item['pass'] is False for item in checks) or closed
    unknown = any(item['pass'] is None for item in checks)
    eligible = not failed and not unknown
    from catalog import verification_state
    status = 'not_eligible' if failed else 'requires_information' if unknown else 'confirmed_eligible' if verification_state(opp)['verification_status'] == 'VERIFIED_LIVE' else 'likely_eligible'
    warnings = [item['detail'] for item in checks if item['pass'] is not True]
    if closed:
        warnings.append('This opportunity is closed or past its stored deadline.')
    others = [title for title in tracked_exclusive_titles if title != opp.get('title')]
    conflict = None
    if (opp.get('is_exclusive_tuition_grant') or rules.get('is_exclusive_tuition_grant')) and others:
        conflict = f"Policy Conflict Alert: {opp['title']} and {', '.join(others)} are marked as exclusive tuition grants in the cached rules. Confirm the current non-duplication terms before accepting awards for the same tuition. Non-tuition perks do not reimburse tuition."
    return {'match_score': round(academic + domicile + skills + gates, 1), 'breakdown': {'academic': academic, 'domicile': domicile, 'skills': skills, 'gates': gates},
            'eligible': eligible, 'eligibility_status': status, 'eligibility_checklist': checks, 'gate_warnings': warnings, 'conflict_warning': conflict,
            'match_note': 'Profile compatibility with recorded criteria; not a probability of selection.'}


def calculate_match(user, opp):
    result = evaluate_match_and_conflicts(user, opp, [])
    points = result['breakdown']
    labels = [('academic', 'Academic compatibility', 35), ('domicile', 'State / domicile', 25), ('skills', 'Skills', 25), ('gates', 'Eligibility conditions', 15)]
    details = {'academic': result['eligibility_checklist'][0]['detail'], 'domicile': result['eligibility_checklist'][1]['detail'],
               'skills': 'No required skills recorded.' if not _skills(opp.get('skills_tags_json') or opp.get('required_skills')) else 'Recorded skill overlap and deterministic vector similarity.',
               'gates': '; '.join(result['gate_warnings']) or 'All recorded conditions are met by the supplied profile.'}
    return {**result, 'overall': result['match_score'], 'academic_match': round(points['academic']/35*100,1),
            'location_match': points['domicile']*4, 'skill_match': round(points['skills']*4,1), 'profile_completeness': round(points['gates']/15*100,1),
            'ai_match_reason': '; '.join(details.values()), 'is_exclusive_tuition_grant': bool(opp.get('is_exclusive_tuition_grant') or parse_eligibility(opp).get('is_exclusive_tuition_grant')),
            'breakdown': [{'factor': label, 'weight': f'{weight} pts', 'points': points[key], 'score': round(points[key]/weight*100,1), 'details': details[key]} for key,label,weight in labels]}


def eligibility_checklist(profile, opportunity):
    return evaluate_match_and_conflicts(profile, opportunity, [])['eligibility_checklist']


def detect_conflicts(opportunities, focus_id=None):
    titles = [o['title'] for o in opportunities if o.get('is_exclusive_tuition_grant') or parse_eligibility(o).get('is_exclusive_tuition_grant')]
    results = []
    for opp in opportunities:
        if focus_id is not None and str(focus_id) not in (str(opp.get('id')), str(opp.get('slug'))):
            continue
        result = evaluate_match_and_conflicts({}, opp, titles)
        if result['conflict_warning']:
            results.append({'opportunity_id': opp.get('id'), 'slug': opp.get('slug'), 'warning': result['conflict_warning']})
    return results


def score_catalog(user, opportunities, saved_ids=None):
    scored = []
    # Merely browsing two scholarships does not mean the student accepted both.
    for opportunity in opportunities:
        opp = {**opportunity, **verification_state_public(opportunity)}
        match = calculate_match(user, opp)
        if opp.get('is_sponsored') and (match['overall'] < 85 or not match['eligible']):
            continue
        scored.append({**opp, 'match': match, 'match_score': match['overall'], 'ai_match_reason': match['ai_match_reason'], 'eligibility_gates': parse_eligibility(opp), 'conflict_warning': None})
    return sorted(scored, key=lambda item: -item['match_score'])


def verification_state_public(opp):
    from catalog import verification_state
    return verification_state(opp)


def compute_deterministic_embedding(text: str) -> List[float]:
    """Stable across processes and machines, unlike Python's randomized hash()."""
    vector = [0.0] * 128
    tokens = re.findall(r'[a-z0-9]+', (text or '').lower())
    for token in tokens:
        digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
        vector[int.from_bytes(digest, 'big') % len(vector)] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 7) for value in vector]


def cosine_similarity(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    norm = math.sqrt(sum(x*x for x in a) * sum(x*x for x in b))
    return sum(x*y for x, y in zip(a, b)) / norm if norm else 0.0
