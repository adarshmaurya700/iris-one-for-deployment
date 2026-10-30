"""Local profile, application-guide, tracking and RFC 5545 services."""
import json
from datetime import date, datetime, timedelta, timezone
from fastapi import HTTPException
from catalog import json_value, utc_now
from database import find_opportunity
from matcher import compute_deterministic_embedding, evaluate_match_and_conflicts

DEMO_PROFILE = {
    'id': 'default_student', 'name': 'Adarsh Maurya', 'email': 'adarsh@usar.ac.in',
    'academic_stage': 'B.Tech 1st Year', 'institution': 'GGSIPU USAR',
    'academic_tier': 'TIER_2_UG_PG', 'state_domicile': 'Delhi', 'age': 19,
    'class_12_pct': 86.0, 'family_income_inr': 480000,
    # Institution ranking must be confirmed by the student, not inferred from a demo profile.
    'nirf_top_50': None, 'skills_json': json.dumps(['Python', 'React', 'FastAPI', 'AI/ML', 'Product Design']),
    'profile_completeness': 85,
}


def student_identity(current_user=None, requested='default_student'):
    if current_user:
        identity = f"user:{current_user['id']}"
        if requested not in ('default_student', identity):
            raise HTTPException(403, 'This student profile belongs to another account.')
        return identity
    if requested != 'default_student':
        raise HTTPException(401, 'Sign in to access a personal student profile.')
    return requested


def save_student_profile(db, student_id, profile, resume_text=None):
    existing = db.execute('SELECT * FROM student_profiles WHERE id = ?', (student_id,)).fetchone()
    data = dict(existing) if existing else {'id': student_id}
    allowed = {'name', 'email', 'academic_stage', 'institution', 'academic_tier', 'state_domicile', 'age', 'class_12_pct', 'family_income_inr', 'nirf_top_50', 'skills_json', 'resume_text', 'profile_completeness', 'embedding_json'}
    data.update({key: val for key, val in profile.items() if key in allowed})
    mappings = {'college': 'institution', 'state': 'state_domicile', 'completeness': 'profile_completeness'}
    for key, dest in mappings.items():
        if key in profile:
            data[dest] = profile[key]
    raw_tier = str(data.get('academic_tier') or profile.get('academic_stage') or profile.get('college') or '')
    if raw_tier and raw_tier not in ('TIER_1_SCHOOL', 'TIER_2_UG_PG'):
        data['academic_stage'] = raw_tier
        data['academic_tier'] = 'TIER_1_SCHOOL' if any(w in raw_tier.lower() for w in ('school', '12th', 'class 12')) else 'TIER_2_UG_PG'
    skills = profile.get('extracted_skills') or profile.get('skills')
    if skills is not None:
        data['skills_json'] = json.dumps(skills if isinstance(skills, list) else [s.strip() for s in skills.split(',')])
    if profile.get('family_income_lpa') is not None:
        data['family_income_inr'] = round(float(profile['family_income_lpa']) * 100000)
    marks = profile.get('cgpa_or_percentage')
    if marks:
        try:
            marks = float(str(marks).strip().rstrip('%'))
            if 10 < marks <= 100:
                data['class_12_pct'] = marks
        except ValueError:
            pass
    if resume_text is not None:
        data['resume_text'] = resume_text
    if data.get('nirf_top_50') is not None:
        data['nirf_top_50'] = int(bool(data['nirf_top_50']))
    data['embedding_json'] = json.dumps(compute_deterministic_embedding(' '.join(json_value(data.get('skills_json'))) + ' ' + str(data.get('academic_stage') or '')))
    columns = list(data)
    db.execute('INSERT INTO student_profiles (' + ', '.join(columns) + ') VALUES (' + ', '.join('?' for _ in columns) + ') ON CONFLICT(id) DO UPDATE SET ' + ', '.join(f'{key} = excluded.{key}' for key in columns if key != 'id'), tuple(data[key] for key in columns))
    db.commit()
    return data


def get_student_profile(db, student_id='default_student', current_user=None):
    row = db.execute('SELECT * FROM student_profiles WHERE id = ?', (student_id,)).fetchone()
    if row:
        return dict(row)
    profile = current_user or DEMO_PROFILE
    return save_student_profile(db, student_id, profile)


def tracked_exclusive_titles(db, student_id):
    rows = db.execute("SELECT o.title FROM tracked_applications t JOIN opportunities o ON t.opportunity_id = o.id WHERE t.student_id = ? AND t.status IN ('In Progress', 'Applied') AND o.is_exclusive_tuition_grant = 1", (student_id,)).fetchall()
    return [row[0] for row in rows]


def how_to_apply(db, opportunity_id, student_id='default_student', current_user=None):
    opp = find_opportunity(db, opportunity_id)
    if not opp:
        raise HTTPException(404, 'Opportunity not found.')
    profile = get_student_profile(db, student_id, current_user)
    match = evaluate_match_and_conflicts(profile, opp, tracked_exclusive_titles(db, student_id))
    tracked = db.execute('SELECT * FROM tracked_applications WHERE student_id = ? AND opportunity_id = ?', (student_id, opp['id'])).fetchone()
    channels = json_value(opp.get('application_channels_json'))
    return {
        'opportunity_id': opp.get('slug') or str(opp['id']), 'title': opp['title'],
        'provider': opp['provider'] or opp['organization'], 'category': opp['category'],
        'benefit_summary': opp['benefit_summary'], 'match_score': match['match_score'],
        'match_breakdown': match['breakdown'], 'eligible': match['eligible'], 'gate_warnings': match['gate_warnings'],
        'verification_status': opp['verification_status'], 'last_verified_at': opp['last_verified_at'],
        'last_checked_at': opp['last_checked_at'], 'deadline_iso': opp['deadline_iso'],
        'is_exclusive_tuition_grant': bool(opp['is_exclusive_tuition_grant']),
        'conflict_warning': match['conflict_warning'], 'application_channels': channels,
        'rules_pdf_url': opp['rules_pdf_url'], 'how_to_apply_steps': json_value(opp['how_to_apply_steps_json']),
        'required_documents': json_value(opp['required_documents_json']),
        'tracking_status': tracked['status'] if tracked else None,
        'checked_documents': json_value(tracked['checked_documents_json']) if tracked else [],
        'verification_note': 'Cached program information. Confirm current eligibility, pricing and application dates on the official portal.' if opp['verification_status'] != 'VERIFIED_LIVE' else 'Live portal check completed at the timestamp shown.',
    }


def track(db, opportunity_id, student_id, status, documents, current_user=None):
    opp = find_opportunity(db, opportunity_id)
    if not opp:
        raise HTTPException(404, 'Opportunity not found.')
    required = json_value(opp['required_documents_json'])
    checked = list(dict.fromkeys(doc for doc in documents if doc in required))
    db.execute('''INSERT INTO tracked_applications (student_id, opportunity_id, status, checked_documents_json, updated_at)
        VALUES (?, ?, ?, ?, ?) ON CONFLICT(student_id, opportunity_id) DO UPDATE SET
        status = excluded.status, checked_documents_json = excluded.checked_documents_json, updated_at = excluded.updated_at''',
        (student_id, opp['id'], status, json.dumps(checked), utc_now()))
    if current_user:
        if status == 'Saved':
            db.execute('DELETE FROM applications WHERE user_id = ? AND opportunity_id = ?', (current_user['id'], opp['id']))
        else:
            db.execute("INSERT INTO applications (user_id, opportunity_id, status) VALUES (?, ?, ?) ON CONFLICT(user_id, opportunity_id) DO UPDATE SET status = excluded.status", (current_user['id'], opp['id'], status))
    db.commit()
    payload = how_to_apply(db, opportunity_id, student_id, current_user)
    payload['tracked_count'] = db.execute("SELECT COUNT(*) FROM tracked_applications WHERE student_id = ? AND status IN ('In Progress', 'Applied')", (student_id,)).fetchone()[0]
    return payload


def _escape_ics(value):
    return str(value or '').replace('\\', '\\\\').replace('\r\n', '\\n').replace('\r', '\\n').replace('\n', '\\n').replace(';', '\\;').replace(',', '\\,')


def _fold_ics(line):
    # RFC 5545 limits physical lines to 75 octets, not 75 Unicode characters.
    result, part = [], ''
    for char in line:
        if len((part + char).encode('utf-8')) > 75:
            result.append(part)
            part = ' '
        part += char
    result.append(part)
    return '\r\n'.join(result)


def calendar_event(opp):
    deadline = opp.get('deadline_iso') or opp.get('deadline')
    try:
        day = date.fromisoformat(str(deadline)[:10])
    except ValueError:
        raise HTTPException(409, 'No confirmed deadline is stored for this opportunity.')
    lines = [
        'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//IRIS onE//Opportunity Calendar//EN',
        'CALSCALE:GREGORIAN', 'METHOD:PUBLISH', 'BEGIN:VEVENT',
        f"UID:iris-{opp.get('slug') or opp['id']}-{day.isoformat()}@iris.one",
        'DTSTAMP:' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
        'DTSTART;VALUE=DATE:' + day.strftime('%Y%m%d'),
        'DTEND;VALUE=DATE:' + (day + timedelta(days=1)).strftime('%Y%m%d'),
        'SUMMARY:' + _escape_ics('Application deadline: ' + opp['title']),
        'DESCRIPTION:' + _escape_ics((opp.get('benefit_summary') or opp.get('description', '')) + '\nConfirm the current deadline on the official portal.\n' + (opp.get('apply_url') or opp.get('url') or '')),
        'URL:' + _escape_ics(opp.get('apply_url') or opp.get('url')),
    ]
    for hours in (72, 24):
        lines.extend(['BEGIN:VALARM', f'TRIGGER:-PT{hours}H', 'ACTION:DISPLAY', 'DESCRIPTION:' + _escape_ics(f"{hours} hours until the application deadline: {opp['title']}"), 'END:VALARM'])
    lines.extend(['END:VEVENT', 'END:VCALENDAR'])
    return '\r\n'.join(_fold_ics(line) for line in lines) + '\r\n'
