"""
Automated background cron scheduler for IRIS onE.
Implements the "Parse Once, Cache Globally" engine to periodically re-verify
deadlines, prune expired opportunities, and update verification audit logs.
"""

import asyncio
from datetime import date, datetime
import json
import os
import sqlite3
from typing import Dict, Any, Optional

from database import get_db, rows_to_list
from seed_data import seed_opportunities

# Default check frequency is 12 hours (configurable via environment variable)
VERIFY_CRON_HOURS = float(os.environ.get("VERIFY_CRON_HOURS", 12.0))

SCHEDULER_STATE: Dict[str, Any] = {
    "status": "stopped",
    "uptime_start_iso": datetime.utcnow().isoformat() + "Z",
    "last_sync_iso": None,
    "sync_count": 0,
    "last_result": None,
    "error_count": 0,
}

_scheduler_task: Optional[asyncio.Task] = None


def refresh_opportunity_catalog(db: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """
    Synchronously updates all opportunities in the database:
    - Syncs any new or missing seed records idempotently.
    - Re-evaluates deadline dates against current date.
    - Sets is_verified_active to 0 if the deadline has passed.
    - Updates verification_log_json with timestamp and status.
    """
    close_db = False
    if db is None:
        db = get_db()
        close_db = True

    try:
        # Idempotently ensure standard catalog items are seeded
        seed_opportunities(db)

        cursor = db.cursor()
        cursor.execute("SELECT * FROM opportunities")
        opps = rows_to_list(cursor.fetchall())

        today = date.today()
        updated_count = 0
        active_count = 0
        expired_count = 0

        for opp in opps:
            opp_id = opp["id"]
            dl_str = (opp.get("deadline") or "").strip()
            days_left = 999
            is_active = 1

            if dl_str:
                try:
                    dl_date = datetime.strptime(dl_str[:10], "%Y-%m-%d").date()
                    days_left = (dl_date - today).days
                    if days_left < 0:
                        is_active = 0
                        expired_count += 1
                    else:
                        active_count += 1
                except Exception:
                    active_count += 1
            else:
                active_count += 1

            existing_log = {}
            raw_log = opp.get("verification_log_json")
            if raw_log:
                try:
                    parsed = json.loads(raw_log)
                    if isinstance(parsed, dict):
                        existing_log = parsed
                    elif isinstance(parsed, list):
                        existing_log = {"pipeline_steps": parsed}
                except Exception:
                    existing_log = {}

            existing_log["last_cron_audit_iso"] = datetime.utcnow().isoformat() + "Z"
            existing_log["days_left"] = days_left
            existing_log["is_verified_active"] = is_active
            existing_log["audit_engine"] = "IRIS-Cron-Scheduler/v1"

            cursor.execute(
                """
                UPDATE opportunities
                SET is_verified_active = ?,
                    verification_log_json = ?
                WHERE id = ?
                """,
                (is_active, json.dumps(existing_log), opp_id),
            )
            updated_count += 1

        db.commit()

        result = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_opportunities": len(opps),
            "updated_count": updated_count,
            "active_count": active_count,
            "expired_count": expired_count,
            "status": "success",
        }

        SCHEDULER_STATE["last_sync_iso"] = result["timestamp"]
        SCHEDULER_STATE["sync_count"] += 1
        SCHEDULER_STATE["last_result"] = result
        return result

    except Exception as e:
        SCHEDULER_STATE["error_count"] += 1
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "error",
            "error": str(e),
        }
    finally:
        if close_db:
            db.close()


async def _background_verification_loop():
    """Continuous background loop sleeping for VERIFY_CRON_HOURS."""
    SCHEDULER_STATE["status"] = "running"
    # Initial catalog refresh upon loop startup
    try:
        refresh_opportunity_catalog()
    except Exception as e:
        print("[Scheduler] Initial catalog refresh error:", e)

    while True:
        try:
            sleep_seconds = max(60, int(VERIFY_CRON_HOURS * 3600))
            await asyncio.sleep(sleep_seconds)
            refresh_opportunity_catalog()
        except asyncio.CancelledError:
            SCHEDULER_STATE["status"] = "stopped"
            break
        except Exception as e:
            SCHEDULER_STATE["error_count"] += 1
            print(f"[Scheduler Error] Background verification failed: {e}")
            await asyncio.sleep(60)


def start_scheduler():
    """Starts the background verification worker task."""
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        SCHEDULER_STATE["status"] = "running"
        _scheduler_task = asyncio.create_task(_background_verification_loop())


def stop_scheduler():
    """Cancels and cleans up the background verification task."""
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        _scheduler_task = None
    SCHEDULER_STATE["status"] = "stopped"


def get_scheduler_status() -> Dict[str, Any]:
    """Returns current runtime state and health metrics of the scheduler."""
    return {
        **SCHEDULER_STATE,
        "cron_interval_hours": VERIFY_CRON_HOURS,
    }
