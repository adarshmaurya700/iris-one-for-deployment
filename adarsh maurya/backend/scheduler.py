"""APScheduler owner lock plus a transactional, cross-process catalog sync lease."""
import asyncio
import json
import os
import threading
import uuid
from datetime import date, datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from catalog import json_value, utc_now
from database import get_db, get_db_path, update_embedding
from matcher import compute_deterministic_embedding

VERIFY_CRON_HOURS = 12
_scheduler = None
_owner_file = None
_owner = uuid.uuid4().hex
_mutex = threading.Lock()
SCHEDULER_STATE = {'status': 'stopped', 'last_sync_iso': None, 'sync_count': 0, 'error_count': 0, 'last_result': None}


def _claim(db):
    now = utc_now()
    expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace('+00:00', 'Z')
    db.execute("INSERT INTO worker_locks (name, owner, expires_at) VALUES ('catalog-sync', '', '') ON CONFLICT(name) DO NOTHING")
    cursor = db.execute("UPDATE worker_locks SET owner = ?, expires_at = ? WHERE name = 'catalog-sync' AND (expires_at < ? OR owner = ?)", (_owner, expiry, now, _owner))
    db.commit()
    return cursor.rowcount == 1


async def _verify_records(opportunities, live):
    from verification import verify_catalog_record
    semaphore = asyncio.Semaphore(4)
    async def verify(opp):
        async with semaphore:
            return opp, await verify_catalog_record(opp, live=live)
    return await asyncio.gather(*(verify(opp) for opp in opportunities))


def run_12h_verification_sync(run_type='12H_SCHEDULED_SYNC', live=True, db=None):
    if not _mutex.acquire(blocking=False):
        return {'status': 'already_running'}
    own_db = db is None
    run_id = None
    claimed = False
    try:
        db = db or get_db()
        claimed = _claim(db)
        if not claimed:
            return {'status': 'already_running'}
        cursor = db.execute('INSERT INTO sync_runs (run_type, status, executed_at) VALUES (?, ?, ?)', (run_type, 'running', utc_now()))
        run_id = cursor.lastrowid
        db.commit()
        opportunities = [dict(row) for row in db.execute('SELECT * FROM opportunities').fetchall()]
        updated = expired = live_count = 0
        for start in range(0, len(opportunities), 4):
            batch = asyncio.run(_verify_records(opportunities[start:start+4], live))
            for opp, check in batch:
                fields = check['fields']
                fields.update({'verification_status': check['verification_status'], 'last_checked_at': check['last_checked_at'],
                               'last_verified_at': check['last_verified_at'], 'verification_log_json': json.dumps(check['trace'])})
                deadline = fields.get('deadline_iso', opp.get('deadline_iso') or opp.get('deadline'))
                is_expired = False
                if deadline:
                    try:
                        is_expired = date.fromisoformat(deadline[:10]) < datetime.now(timezone(timedelta(hours=5, minutes=30))).date()
                    except ValueError:
                        pass
                closed = check['verification_status'] in ('CLOSED', 'EXPIRED') or is_expired
                if is_expired:
                    fields['verification_status'] = 'EXPIRED'
                fields['is_verified_active'] = 0 if closed else 1 if check['verification_status'] == 'VERIFIED_LIVE' else opp['is_verified_active']
                if check['verification_status'] != 'VERIFIED_LIVE':
                    channels = json_value(opp.get('application_channels_json'))
                    for channel in channels:
                        channel['verified'] = False
                        channel['badge'] = 'Open'
                    fields['application_channels_json'] = json.dumps(channels)
                db.execute('UPDATE opportunities SET ' + ', '.join(f'{key} = ?' for key in fields) + ' WHERE id = ?', tuple(fields.values()) + (opp['id'],))
                merged = {**opp, **fields}
                update_embedding(db, opp['id'], compute_deterministic_embedding(' '.join(str(merged.get(k) or '') for k in ('title', 'description', 'tags', 'required_skills'))))
                updated += 1
                expired += int(closed)
                live_count += int(fields['verification_status'] == 'VERIFIED_LIVE')
            expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace('+00:00', 'Z')
            db.execute("UPDATE worker_locks SET expires_at = ? WHERE name = 'catalog-sync' AND owner = ?", (expiry, _owner))
            db.commit()
        active = db.execute('SELECT COUNT(*) FROM opportunities WHERE is_verified_active = 1').fetchone()[0]
        summary = {'status': 'completed', 'total_opportunities': len(opportunities), 'opportunities_updated': updated,
                   'expired_count': expired, 'active_count': active, 'live_verified_count': live_count,
                   'fake_links_purged': 0, 'mode': 'live' if live_count else 'cache_only', 'executed_at': utc_now()}
        db.execute('UPDATE sync_runs SET status = ?, opportunities_updated = ?, fake_links_purged = ?, completed_at = ?, summary_json = ? WHERE id = ?', ('completed', updated, expired, utc_now(), json.dumps(summary), run_id))
        db.commit()
        SCHEDULER_STATE.update(last_sync_iso=summary['executed_at'], sync_count=SCHEDULER_STATE['sync_count'] + 1, last_result=summary)
        return summary
    except Exception as exc:
        if db is not None:
            db.rollback()
        SCHEDULER_STATE['error_count'] += 1
        summary = {'status': 'failed', 'error': type(exc).__name__}
        if run_id:
            db.execute('UPDATE sync_runs SET status = ?, completed_at = ?, summary_json = ? WHERE id = ?', ('failed', utc_now(), json.dumps(summary), run_id))
            db.commit()
        return summary
    finally:
        if claimed:
            db.execute("DELETE FROM worker_locks WHERE name = 'catalog-sync' AND owner = ?", (_owner,))
            db.commit()
        if own_db and db is not None:
            db.close()
        _mutex.release()


def refresh_opportunity_catalog(db=None):
    return run_12h_verification_sync(run_type='ON_DEMAND_SCAN', live=False, db=db)


def _acquire_scheduler_owner():
    global _owner_file
    _owner_file = open(get_db_path() + '.scheduler.lock', 'a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            _owner_file.seek(0)
            if not _owner_file.read(1):
                _owner_file.write(b'0')
                _owner_file.flush()
            _owner_file.seek(0)
            msvcrt.locking(_owner_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(_owner_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        _owner_file.close()
        _owner_file = None
        return False


def start_scheduler():
    global _scheduler
    if os.environ.get('IRIS_DISABLE_SCHEDULER') == '1':
        SCHEDULER_STATE['status'] = 'disabled'
        return
    if _scheduler and _scheduler.running:
        return
    if not _acquire_scheduler_owner():
        SCHEDULER_STATE['status'] = 'standby'
        return
    _scheduler = BackgroundScheduler(timezone='UTC')
    status = get_scheduler_status()
    next_run = datetime.now(timezone.utc)
    if status['last_sync_iso']:
        next_run = max(next_run, datetime.fromisoformat(status['last_sync_iso'].replace('Z', '+00:00')) + timedelta(hours=12))
    _scheduler.add_job(run_12h_verification_sync, IntervalTrigger(hours=12), id='catalog-verification',
                       next_run_time=next_run, max_instances=1, coalesce=True, misfire_grace_time=300)
    _scheduler.start()
    SCHEDULER_STATE['status'] = 'running'


def stop_scheduler():
    global _scheduler, _owner_file
    if _scheduler:
        _scheduler.shutdown(wait=True)
        _scheduler = None
    if _owner_file:
        _owner_file.close()
        _owner_file = None
    SCHEDULER_STATE['status'] = 'stopped'


def get_scheduler_status():
    db = get_db()
    try:
        latest = db.execute("SELECT * FROM sync_runs WHERE status = 'completed' ORDER BY id DESC LIMIT 1").fetchone()
        running = db.execute("SELECT owner FROM worker_locks WHERE name = 'catalog-sync' AND expires_at > ?", (utc_now(),)).fetchone()
        verified = db.execute("SELECT MAX(last_verified_at) FROM opportunities").fetchone()[0]
        last = latest['completed_at'] if latest else None
        next_run = datetime.fromisoformat(last.replace('Z', '+00:00')) + timedelta(hours=12) if last else datetime.now(timezone.utc)
        job = _scheduler.get_job('catalog-verification') if _scheduler else None
        if job and hasattr(job, 'next_run_time') and job.next_run_time:
            next_run = job.next_run_time
        return {**SCHEDULER_STATE, 'cron_interval_hours': 12, 'last_sync_iso': last,
                'last_verified_at': verified or None, 'next_run_at': next_run.isoformat(),
                'seconds_until_next_run': max(0, int((next_run - datetime.now(timezone.utc)).total_seconds())),
                'sync_running': bool(running), 'last_result': json_value(latest['summary_json'], {}) if latest else None}
    finally:
        db.close()
