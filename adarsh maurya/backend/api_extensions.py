"""Application and cache APIs; included before legacy dynamic routes."""
from typing import Literal, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from auth import get_optional_current_user
from database import db_session, find_opportunity
from application_service import how_to_apply, student_identity, track, calendar_event
from ai_assistant import ask_local_cache
from scheduler import get_scheduler_status, run_12h_verification_sync

router = APIRouter()


class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    student_id: str = 'default_student'
    opportunity_id: Optional[str] = None


class TrackRequest(BaseModel):
    opportunity_id: str
    student_id: str = 'default_student'
    status: Literal['Saved', 'In Progress', 'Applied'] = 'In Progress'
    checked_documents: list[str] = Field(default_factory=list, max_length=100)


class SyncRequest(BaseModel):
    live: bool = True


@router.get('/api/sync/status')
def sync_status():
    return get_scheduler_status()


@router.post('/api/sync/trigger', status_code=202)
def sync_trigger(background_tasks: BackgroundTasks, req: SyncRequest = SyncRequest()):
    if get_scheduler_status()['sync_running']:
        return {'status': 'already_running'}
    background_tasks.add_task(run_12h_verification_sync, run_type='ON_DEMAND_SCAN', live=req.live)
    return {'status': 'queued', 'mode': 'live_if_configured' if req.live else 'cache_only'}


@router.post('/api/assistant/ask')
async def ask(req: AskRequest, current_user=Depends(get_optional_current_user), db=Depends(db_session)):
    identity = student_identity(current_user, req.student_id)
    return await ask_local_cache(req.query, identity, db, req.opportunity_id, current_user)


@router.get('/api/opportunities/{opportunity_id}/how-to-apply')
def guide(opportunity_id: str, student_id: str = 'default_student', current_user=Depends(get_optional_current_user), db=Depends(db_session)):
    return how_to_apply(db, opportunity_id, student_identity(current_user, student_id), current_user)


@router.post('/api/applications/track')
def track_application(req: TrackRequest, current_user=Depends(get_optional_current_user), db=Depends(db_session)):
    return track(db, req.opportunity_id, student_identity(current_user, req.student_id), req.status, req.checked_documents, current_user)


@router.get('/api/applications/tracked')
def tracked_applications(current_user=Depends(get_optional_current_user), db=Depends(db_session)):
    identity = student_identity(current_user)
    return [dict(row) for row in db.execute('''SELECT t.status, t.checked_documents_json,
        o.slug AS opportunity_id, o.id AS db_id FROM tracked_applications t
        JOIN opportunities o ON o.id = t.opportunity_id WHERE t.student_id = ?''', (identity,)).fetchall()]


@router.get('/api/opportunities/{opportunity_id}/calendar.ics')
def calendar(opportunity_id: str, db=Depends(db_session)):
    opp = find_opportunity(db, opportunity_id)
    if not opp:
        raise HTTPException(404, 'Opportunity not found.')
    filename = (opp.get('slug') or str(opp['id'])).replace('"', '').replace('\r', '').replace('\n', '')
    return Response(calendar_event(opp), media_type='text/calendar', headers={'Content-Disposition': f'attachment; filename="{filename}-deadline.ics"'})
