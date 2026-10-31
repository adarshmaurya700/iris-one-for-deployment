"""Profile, saved feed and application workspace APIs for the paper frontend."""
import json
import os
from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from auth import get_workspace_user
from application_service import get_student_profile, save_student_profile, student_identity, calendar_event
from catalog import json_value, utc_now
from database import db_session, find_opportunity, PostgresConnection
from matcher import calculate_match
from catalog import verification_state
from runtime_config import mode, credential
from security import require_admin

router = APIRouter()


class ProfileInput(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    age: Optional[int] = Field(default=None, ge=10, le=100)
    state_domicile: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=80)
    academic_stage: Optional[str] = Field(default=None, max_length=120)
    institution: Optional[str] = Field(default=None, max_length=200)
    graduation_year: Optional[int] = Field(default=None, ge=2000, le=2100)
    class_12_pct: Optional[float] = Field(default=None, ge=0, le=100)
    family_income_inr: Optional[int] = Field(default=None, ge=0)
    nirf_top_50: Optional[bool] = None
    skills: Optional[list[str]] = Field(default=None, max_length=40)
    domains: Optional[list[Literal['Scholarships', 'Internships', 'Hackathons', 'Competitions', 'Student Offers', 'International']]] = None
    areas_of_interest: Optional[str] = Field(default=None, max_length=400)
    onboarding_complete: Optional[bool] = None
    preferences: Optional[dict[Literal['reduce_motion', 'compact_cards', 'show_verification'], bool]] = None


def profile_payload(profile):
    data = {key: value for key, value in profile.items() if key not in ('resume_text', 'embedding_json')}
    data['skills'] = json_value(profile.get('skills_json'))
    data['domains'] = json_value(profile.get('domains_json'))
    data['preferences'] = json_value(profile.get('preferences_json'), {})
    data['workspace_kind'] = 'account' if profile['id'].startswith('user:') else 'guest' if profile['id'].startswith('guest:') else 'sample'
    fields = [('name', 10), ('age', 5), ('state_domicile', 5), ('country', 5), ('academic_stage', 15), ('institution', 10), ('graduation_year', 5), ('skills_json', 15), ('domains_json', 10), ('resume_filename', 20)]
    data['profile_completeness'] = sum(points for field, points in fields if (json_value(profile.get(field)) if field.endswith('_json') else profile.get(field)))
    return data


@router.get('/api/profile')
def profile(current_user=Depends(get_workspace_user), db=Depends(db_session)):
    return profile_payload(get_student_profile(db, student_identity(current_user), current_user))


@router.post('/api/profile/update')
def update_profile(req: ProfileInput, current_user=Depends(get_workspace_user), db=Depends(db_session)):
    identity = student_identity(current_user)
    get_student_profile(db, identity, current_user)
    values = req.model_dump(exclude_unset=True)
    nullable = {'age', 'graduation_year', 'class_12_pct', 'family_income_inr', 'nirf_top_50'}
    for key in list(values):
        if values[key] is None and key not in nullable:
            del values[key]
    if 'skills' in values:
        values['skills_json'] = json.dumps(list(dict.fromkeys(skill.strip()[:60] for skill in values.pop('skills') if skill.strip())))
    if 'domains' in values:
        values['domains_json'] = json.dumps(list(dict.fromkeys(values.pop('domains'))))
    if 'preferences' in values:
        existing = get_student_profile(db, identity, current_user)
        values['preferences_json'] = json.dumps({**json_value(existing.get('preferences_json'), {}), **values.pop('preferences')})
    if 'onboarding_complete' in values:
        values['onboarding_complete'] = int(values['onboarding_complete'])
    if 'academic_stage' in values:
        stage = values['academic_stage'].lower()
        values['academic_tier'] = 'TIER_1_SCHOOL' if any(word in stage for word in ('class ', 'school', '12th', '11th')) else 'TIER_2_UG_PG'
    saved = save_student_profile(db, identity, values)
    if current_user:
        mapping = {'name': 'name', 'age': 'age', 'state_domicile': 'state', 'country': 'country', 'academic_stage': 'college'}
        updates = {target: values[source] for source, target in mapping.items() if source in values}
        if 'skills_json' in values:
            updates['skills'] = ', '.join(json_value(values['skills_json']))
            updates['extracted_skills'] = updates['skills']
        if 'domains_json' in values:
            updates['domains'] = ', '.join(json_value(values['domains_json']))
        if updates:
            db.execute('UPDATE users SET ' + ', '.join(f'{key} = ?' for key in updates) + ' WHERE id = ?', tuple(updates.values()) + (current_user['id'],))
            db.commit()
    return profile_payload(saved)


def public_opportunity(db, record, current_user=None):
    item = {**dict(record), **verification_state(dict(record))}
    profile = get_student_profile(db, student_identity(current_user), current_user)
    match = calculate_match(profile, item)
    item.update(db_id=item['id'], id=item.get('slug') or str(item['id']), match=match, match_score=match['overall'])
    return item


def saved_rows(db, current_user=None):
    identity = student_identity(current_user)
    sql = 'SELECT o.* FROM opportunities o WHERE o.id IN (SELECT opportunity_id FROM profile_saved WHERE student_id = ?)'
    params = [identity]
    if current_user:
        sql += ' OR o.id IN (SELECT opportunity_id FROM saved_opportunities WHERE user_id = ?)'
        params.append(current_user['id'])
    return db.execute(sql, tuple(params)).fetchall()


@router.get('/api/opportunities/saved')
def saved_feed(current_user=Depends(get_workspace_user), db=Depends(db_session)):
    return [{**public_opportunity(db, row, current_user), 'is_saved': True} for row in saved_rows(db, current_user)]


@router.post('/api/opportunities/{opportunity_id}/save')
def save(opportunity_id: str, current_user=Depends(get_workspace_user), db=Depends(db_session)):
    opp = find_opportunity(db, opportunity_id)
    if not opp:
        raise HTTPException(404, 'Opportunity not found.')
    db.execute('INSERT INTO profile_saved (student_id, opportunity_id, created_at) VALUES (?, ?, ?) ON CONFLICT(student_id, opportunity_id) DO NOTHING', (student_identity(current_user), opp['id'], utc_now()))
    if current_user:
        db.execute('INSERT INTO saved_opportunities (user_id, opportunity_id) VALUES (?, ?) ON CONFLICT(user_id, opportunity_id) DO NOTHING', (current_user['id'], opp['id']))
    db.commit()
    return {'saved': True, 'opportunity_id': opportunity_id}


@router.delete('/api/opportunities/{opportunity_id}/save')
def unsave(opportunity_id: str, current_user=Depends(get_workspace_user), db=Depends(db_session)):
    opp = find_opportunity(db, opportunity_id)
    if not opp:
        raise HTTPException(404, 'Opportunity not found.')
    db.execute('DELETE FROM profile_saved WHERE student_id = ? AND opportunity_id = ?', (student_identity(current_user), opp['id']))
    if current_user:
        db.execute('DELETE FROM saved_opportunities WHERE user_id = ? AND opportunity_id = ?', (current_user['id'], opp['id']))
    db.commit()
    return {'saved': False, 'opportunity_id': opportunity_id}


@router.get('/api/applications/overview')
def applications(current_user=Depends(get_workspace_user), db=Depends(db_session)):
    identity = student_identity(current_user)
    rows = db.execute('''SELECT o.*, t.status AS application_status, t.updated_at,
        t.checked_documents_json FROM tracked_applications t JOIN opportunities o
        ON o.id = t.opportunity_id WHERE t.student_id = ? AND t.status != 'Saved' ORDER BY t.updated_at DESC''', (identity,)).fetchall()
    items = [public_opportunity(db, row, current_user) for row in rows]
    known = {item['db_id'] for item in items}
    if current_user:
        legacy = db.execute('''SELECT o.*, a.status AS application_status, a.created_at AS updated_at
            FROM applications a JOIN opportunities o ON o.id = a.opportunity_id WHERE a.user_id = ?''', (current_user['id'],)).fetchall()
        items.extend(public_opportunity(db, row, current_user) for row in legacy if row['id'] not in known)
    return {'applications': items, 'tracked_count': len(items)}


@router.delete('/api/applications/tracked/{opportunity_id}')
def untrack(opportunity_id: str, current_user=Depends(get_workspace_user), db=Depends(db_session)):
    opp = find_opportunity(db, opportunity_id)
    if not opp:
        raise HTTPException(404, 'Opportunity not found.')
    db.execute('DELETE FROM tracked_applications WHERE student_id = ? AND opportunity_id = ?', (student_identity(current_user), opp['id']))
    if current_user:
        db.execute('DELETE FROM applications WHERE user_id = ? AND opportunity_id = ?', (current_user['id'], opp['id']))
    db.commit()
    return {'removed': True, 'opportunity_id': opportunity_id}


@router.get('/api/applications/calendar.ics')
def application_calendar(current_user=Depends(get_workspace_user), db=Depends(db_session)):
    records = applications(current_user, db)['applications']
    events = []
    for opp in records:
        try:
            data = calendar_event(opp)
            events.append('BEGIN:VEVENT' + data.split('BEGIN:VEVENT', 1)[1].split('END:VEVENT', 1)[0] + 'END:VEVENT\r\n')
        except HTTPException:
            continue
    if not events:
        raise HTTPException(409, 'Track an opportunity with a confirmed deadline to export reminders.')
    content = 'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//IRIS onE//Application Calendar//EN\r\nCALSCALE:GREGORIAN\r\n' + ''.join(events) + 'END:VCALENDAR\r\n'
    return Response(content, media_type='text/calendar', headers={'Content-Disposition': 'attachment; filename="iris-application-reminders.ics"'})


@router.get('/api/platform/config')
def platform_config(db=Depends(db_session)):
    return {'database': 'PostgreSQL' if isinstance(db, PostgresConnection) else 'SQLite WAL',
            'catalog_count': db.execute('SELECT COUNT(*) FROM opportunities').fetchone()[0],
            'operating_mode': mode(), 'is_simulated': mode() == 'demo',
            'live_verification_configured': mode() == 'live' and bool(credential('TINYFISH_API_KEY') and credential('GEMINI_API_KEY')),
            'assistant_providers': ['Local retrieval (demo)'] if mode() == 'demo' else [label for key, label in [('GEMINI_API_KEY', 'Gemini'), ('GROQ_API_KEY', 'Groq'), ('OLLAMA_BASE_URL', 'Ollama')] if os.environ.get(key)] or ['Local retrieval'],
            'sync_interval_hours': 12}


@router.get('/api/admin/diagnostics', dependencies=[Depends(require_admin)])
def integration_diagnostics(db=Depends(db_session)):
    from diagnostics import snapshot
    from scheduler import get_scheduler_status
    return {**snapshot(), 'database': 'PostgreSQL' if isinstance(db, PostgresConnection) else 'SQLite WAL',
            'database_connected': db.execute('SELECT 1').fetchone()[0] == 1,
            'scheduler': get_scheduler_status()}


@router.get('/api/profile/export')
def export_profile(current_user=Depends(get_workspace_user), db=Depends(db_session)):
    identity = student_identity(current_user)
    data = {'exported_at': utc_now(), 'profile': profile_payload(get_student_profile(db, identity, current_user)),
            'saved': saved_feed(current_user, db), 'applications': applications(current_user, db)['applications']}
    return Response(json.dumps(data, ensure_ascii=False, default=str), media_type='application/json',
                    headers={'Content-Disposition': 'attachment; filename="iris-workspace.json"'})


@router.delete('/api/profile/resume')
def remove_resume(current_user=Depends(get_workspace_user), db=Depends(db_session)):
    identity = student_identity(current_user)
    get_student_profile(db, identity, current_user)
    saved = save_student_profile(db, identity, {'resume_text': '', 'resume_filename': '', 'resume_uploaded_at': ''})
    if current_user:
        db.execute("UPDATE users SET profile_json = '' WHERE id = ?", (current_user['id'],))
        db.commit()
    return profile_payload(saved)
