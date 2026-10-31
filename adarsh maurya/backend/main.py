"""
Main FastAPI application for IRIS one — Student Opportunity Matching Platform.
Provides complete REST API endpoints for authentication, opportunity discovery,
matching algorithm scoring, bookmarks, applications, dashboard statistics, and search.
"""
from web_search import search_web_opportunities
import json
import os
import sqlite3
import time
import uuid
import jwt
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

import env_loader  # noqa: F401

from fastapi import FastAPI, Depends, HTTPException, Query, status, UploadFile, File, Form, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from database import init_db, get_db, db_session, row_to_dict, rows_to_list, find_opportunity, DB_PATH
from application_service import get_student_profile, student_identity, save_student_profile
from catalog import today_in_india, verification_state
from runtime_config import mode, production, validate_runtime
from security import SlidingWindowRateLimiter, assistant_limit, verification_limit, auth_limit, require_admin, require_verification_access
from seed_data import seed_opportunities, upsert_opportunity
from matcher import calculate_match, score_catalog, parse_eligibility, eligibility_checklist, detect_conflicts
from auth import (
    SECRET_KEY,
    hash_password,
    verify_password,
    create_token,
    get_current_user,
    get_optional_current_user,
    get_workspace_user,
)
from tinyfish_pipeline import run_verification_pipeline, discover_and_verify
from gemini_extractor import verified_to_db_row
from resume_analyzer import (
    analyze_resume_bytes,
    persist_profile_to_user,
    load_sample_resume_text,
    SAMPLE_PROFILE,
)
from scheduler import (
    start_scheduler,
    stop_scheduler,
    get_scheduler_status,
    refresh_opportunity_catalog,
)
from legacy_ai_assistant import process_assistant_chat

# ---------------------------------------------------------------------------
# Lifespan: DB initialization, auto-seeding & Background Cron Scheduler
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_runtime()
    # Initialize DB schemas on startup
    init_db()
    conn = get_db()
    try:
        if mode() == 'demo' or os.environ.get('IRIS_SEED_REFERENCE') == '1':
            seed_opportunities(conn)
    finally:
        conn.close()

    # Start the automated background cron scheduler (parse once, cache globally)
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


# ---------------------------------------------------------------------------
# FastAPI App Initialization, Security Headers & CORS
# ---------------------------------------------------------------------------
app = FastAPI(
    title="IRIS one API",
    description="Student Opportunity Matching & Verification Platform Backend",
    version="1.0.0",
    lifespan=lifespan,
)
from api_extensions import router as application_router
app.include_router(application_router)
from frontend_api import router as frontend_router
app.include_router(frontend_router)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    from application_service import guest_identity
    cookie = request.cookies.get('iris_workspace', '')
    identity = None
    if cookie:
        try:
            payload = jwt.decode(cookie, SECRET_KEY, algorithms=['HS256'])
            candidate = payload.get('sub', '')
            if isinstance(candidate, str) and candidate.startswith('guest:') and len(candidate) == 38 and payload.get('mode') == mode():
                identity = candidate
        except jwt.PyJWTError:
            pass
    new_cookie = identity is None
    if new_cookie:
        identity = 'guest:' + uuid.uuid4().hex
        cookie = jwt.encode({'sub': identity, 'mode': mode(), 'exp': datetime.now(timezone.utc) + timedelta(days=7)}, SECRET_KEY, algorithm='HS256')
    context = guest_identity.set(identity)
    try:
        response = await call_next(request)
    finally:
        guest_identity.reset(context)
    if new_cookie:
        response.set_cookie('iris_workspace', cookie, max_age=7 * 86400, httponly=True, secure=production() or request.url.scheme == 'https', samesite='lax')
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'"
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    if production():
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

@app.middleware('http')
async def bounded_request_body(request: Request, call_next):
    if request.method in ('POST', 'PUT', 'PATCH'):
        limit = 6 * 1024 * 1024 if request.url.path == '/api/resume/analyze' else 256 * 1024
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > limit:
                return JSONResponse({'detail': 'Request body exceeds the allowed size.'}, status_code=413)
            chunks.append(chunk)
        request._body = b''.join(chunks)
    return await call_next(request)


# Configurable CORS via ALLOWED_ORIGINS (default '*' in dev)
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "").strip()
if not allowed_origins_env:
    origins = []
elif allowed_origins_env == "*":
    origins = ["*"]
else:
    origins = [orig.strip() for orig in allowed_origins_env.split(",") if orig.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials="*" not in origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Sliding-Window In-Memory Rate Limiter (Protects AI Billing & Uploads)
# ---------------------------------------------------------------------------
# Rate limiter instances for expensive routes
ai_rate_limiter = verification_limit
resume_rate_limiter = SlidingWindowRateLimiter(
    max_requests=5,
    window_seconds=600,
    scope="Resume analysis upload rate limit",
)

chat_rate_limiter = assistant_limit

# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
class UserSignup(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=1, max_length=120)

    @field_validator('password')
    @classmethod
    def password_bytes(cls, value):
        if len(value.encode('utf-8')) > 72:
            raise ValueError('Password must contain at most 72 UTF-8 bytes.')
        return value

    @field_validator('email')
    @classmethod
    def email_format(cls, value):
        import re
        value = value.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Enter a valid email address.')
        return value
    college: Optional[str] = ""
    age: Optional[int] = 0
    state: Optional[str] = ""
    country: Optional[str] = "India"
    skills: Optional[str] = ""
    domains: Optional[str] = ""


class UserLogin(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=72)



class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    college: Optional[str] = None
    age: Optional[int] = None
    state: Optional[str] = None
    country: Optional[str] = None
    skills: Optional[str] = None
    domains: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    class_12_pct: Optional[float] = Field(default=None, ge=0, le=100)
    family_income_inr: Optional[int] = Field(default=None, ge=0)
    nirf_top_50: Optional[bool] = None


# ---------------------------------------------------------------------------
# Auth Routes (/api/auth)
# ---------------------------------------------------------------------------
@app.post("/api/auth/signup", status_code=status.HTTP_201_CREATED, dependencies=[Depends(auth_limit.check)])
def signup(data: UserSignup, db: sqlite3.Connection = Depends(db_session)):
    """Creates a new student user, hashes password, and returns a JWT token."""
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(?)", (data.email.strip(),))
    if cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    pwd_hash = hash_password(data.password)
    cursor.execute(
        """
        INSERT INTO users (email, password_hash, name, college, age, state, country, skills, domains)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.email.strip().lower(),
            pwd_hash,
            data.name.strip(),
            (data.college or "").strip(),
            data.age or 0,
            (data.state or "").strip(),
            (data.country or "India").strip(),
            (data.skills or "").strip(),
            (data.domains or "").strip(),
        ),
    )
    db.commit()
    user_id = cursor.lastrowid

    token = create_token(user_id)

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user_dict = row_to_dict(cursor.fetchone())
    if user_dict and "password_hash" in user_dict:
        del user_dict["password_hash"]

    return {
        "message": "User registered successfully",
        "token": token,
        "user": user_dict,
    }


@app.post("/api/auth/login", dependencies=[Depends(auth_limit.check)])
def login(data: UserLogin, db: sqlite3.Connection = Depends(db_session)):
    """Verifies user credentials and returns a JWT access token."""
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (data.email.strip(),))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    user_dict = row_to_dict(row)
    if not verify_password(data.password, user_dict["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_token(user_dict["id"])
    del user_dict["password_hash"]

    return {
        "message": "Login successful",
        "token": token,
        "user": user_dict,
    }


@app.get("/api/auth/me")
def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns the authenticated student's profile."""
    return current_user


@app.put("/api/auth/profile")
def update_profile(
    data: ProfileUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(db_session),
):
    """Updates profile attributes (name, college, age, state, country, skills, domains)."""
    user_id = current_user["id"]
    cursor = db.cursor()

    updates = []
    params = []

    if data.name is not None:
        updates.append("name = ?")
        params.append(data.name.strip())
    if data.college is not None:
        updates.append("college = ?")
        params.append(data.college.strip())
    if data.age is not None:
        updates.append("age = ?")
        params.append(data.age)
    if data.state is not None:
        updates.append("state = ?")
        params.append(data.state.strip())
    if data.country is not None:
        updates.append("country = ?")
        params.append(data.country.strip())
    if data.skills is not None:
        updates.append("skills = ?")
        params.append(data.skills.strip())
    if data.domains is not None:
        updates.append("domains = ?")
        params.append(data.domains.strip())
    if data.telegram_chat_id is not None:
        updates.append("telegram_chat_id = ?")
        params.append(data.telegram_chat_id.strip())

    if updates:
        params.append(user_id)
        sql = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(sql, tuple(params))
        db.commit()

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    updated_user = row_to_dict(cursor.fetchone())
    if updated_user and "password_hash" in updated_user:
        del updated_user["password_hash"]
    if updated_user:
        saved_profile = save_student_profile(db, student_identity(updated_user), {**updated_user, **data.model_dump(exclude_none=True)})
        updated_user['student_profile'] = saved_profile

    return updated_user


# ---------------------------------------------------------------------------
# Health & Production Admin Routes (/api/health, /api/admin)
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health_check(db: sqlite3.Connection = Depends(db_session)):
    """
    Production health check returning connection status, DB path,
    opportunity metrics, user counts, and background scheduler telemetry.
    """
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM opportunities")
    opp_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM opportunities WHERE is_verified_active = 1")
    active_opp_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    return {
        "status": "ok",
        "service": "IRIS onE API",
        "operating_mode": mode(),
        "version": "1.0.0",
        "database": {
            "status": "connected",
            "engine": "PostgreSQL" if hasattr(db, "raw") else "SQLite",
            "total_opportunities": opp_count,
            "active_catalog_records": active_opp_count,
            "active_verified_opportunities": sum(verification_state(dict(row))["is_live_verified"] for row in db.execute("SELECT * FROM opportunities").fetchall()),

        },
        "scheduler": get_scheduler_status(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


@app.post("/api/admin/refresh-catalog", dependencies=[Depends(require_admin)])
def admin_refresh_catalog(db: sqlite3.Connection = Depends(db_session)):
    """
    Admin endpoint to trigger immediate catalog re-audit, pruning expired
    deadlines and updating verified statuses.
    """
    result = refresh_opportunity_catalog(db)
    return {
        "message": "Opportunity catalog successfully audited and refreshed.",
        "audit_summary": result,
    }


def workspace_sets(db, user=None):
    identity = student_identity(user)
    saved = {row[0] for row in db.execute('SELECT opportunity_id FROM profile_saved WHERE student_id = ?', (identity,)).fetchall()}
    applied = {row[0] for row in db.execute("SELECT opportunity_id FROM tracked_applications WHERE student_id = ? AND status != 'Saved'", (identity,)).fetchall()}
    if user:
        saved |= {row[0] for row in db.execute('SELECT opportunity_id FROM saved_opportunities WHERE user_id = ?', (user['id'],)).fetchall()}
        applied |= {row[0] for row in db.execute('SELECT opportunity_id FROM applications WHERE user_id = ?', (user['id'],)).fetchall()}
    return saved, applied


# ---------------------------------------------------------------------------
# Opportunity Routes (/api/opportunities)
# ---------------------------------------------------------------------------
@app.get("/api/opportunities")
def list_opportunities(
    category: Optional[str] = Query(None, description="Filter by opportunity type"),
    search: Optional[str] = Query(None, description="Search query across title, org, tags"),
    sort: Optional[str] = Query("match", description="Sort by 'match' (default) or 'deadline'"),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    db: sqlite3.Connection = Depends(db_session),
):
    """
    List all opportunities with match scores computed for the user.
    Supports filtering by category/type and search keyword, and sorting by match score or deadline.
    """
    cursor = db.cursor()
    query_parts = ["SELECT * FROM opportunities WHERE is_verified_active = 1 AND (deadline_iso = '' OR deadline_iso >= ?)"]
    params: List[Any] = [today_in_india().isoformat()]

    if category:
        query_parts.append("AND (LOWER(type) = LOWER(?) OR LOWER(category) = LOWER(?))")
        params.extend([category.strip(), category.strip()])

    if search:
        s = f"%{search.strip().lower()}%"
        query_parts.append(
            "AND (LOWER(title) LIKE ? OR LOWER(organization) LIKE ? OR LOWER(description) LIKE ? OR LOWER(tags) LIKE ?)"
        )
        params.extend([s, s, s, s])

    cursor.execute(" ".join(query_parts), tuple(params))
    rows = cursor.fetchall()
    opps = rows_to_list(rows)

    # Saved and applied IDs for the user
    saved_ids, applied_ids = workspace_sets(db, current_user)

    profile = get_student_profile(db, student_identity(current_user), current_user)
    opps = score_catalog(profile, opps, saved_ids)
    for opp in opps:
        opp.update(verification_state(opp))
        public_id = opp.get("slug") or opp["id"]
        opp["db_id"] = opp["id"]
        opp["id"] = public_id
        opp["is_saved"] = opp["db_id"] in saved_ids
        opp["is_applied"] = opp["db_id"] in applied_ids

    # Sorting
    if sort == "deadline":
        opps.sort(key=lambda x: x.get("deadline") or "9999-12-31")
    else:
        # Default: sort by match score descending
        opps.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    return opps

web_search_rate_limiter = SlidingWindowRateLimiter(
    max_requests=20,
    window_seconds=600,
    scope="Web search rate limit",
)


@app.get("/api/opportunities/web-search", dependencies=[Depends(web_search_rate_limiter.check)])
async def web_search_route(q: str = Query(..., min_length=3, max_length=120)):
    try:
        return await search_web_opportunities(q)
    except Exception as e:
        return {"results": [], "mode": "error", "error": "Web search is unavailable; please try again later."}

@app.get("/api/opportunities/{opportunity_id}")
def get_opportunity(
    opportunity_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    db: sqlite3.Connection = Depends(db_session),
):
    """Returns single opportunity details with complete match breakdown."""
    opp = find_opportunity(db, opportunity_id)
    if not opp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity with ID {opportunity_id} not found.",
        )
    opportunity_id = opp["id"]
    cursor = db.cursor()
    profile = get_student_profile(db, student_identity(current_user), current_user)
    match_info = calculate_match(profile, opp)
    opp["match"] = match_info
    opp["match_score"] = match_info["overall"]

    saved_ids, applied_ids = workspace_sets(db, current_user)
    is_saved, is_applied = opportunity_id in saved_ids, opportunity_id in applied_ids

    opp["is_saved"] = is_saved
    opp["is_applied"] = is_applied
    opp["db_id"] = opp["id"]
    opp["id"] = opp.get("slug") or opp["id"]
    opp["eligibility_gates"] = parse_eligibility(opp)
    opp["eligibility_checklist"] = eligibility_checklist(profile, opp)
    opp.update(verification_state(opp))
    opp["ai_match_reason"] = match_info.get("ai_match_reason")

    return opp


# ---------------------------------------------------------------------------
# Saved / Bookmark Routes (/api/saved)
# ---------------------------------------------------------------------------
@app.post("/api/saved/{opportunity_id}")
def save_opportunity(
    opportunity_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(db_session),
):
    """Save or bookmark an opportunity for the logged-in student."""
    opp = find_opportunity(db, opportunity_id)
    if not opp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity with ID or slug {opportunity_id} does not exist.",
        )
    real_id = opp["id"]

    cursor = db.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO saved_opportunities (user_id, opportunity_id) VALUES (?, ?)",
        (current_user["id"], real_id),
    )
    from catalog import utc_now
    cursor.execute('INSERT INTO profile_saved (student_id, opportunity_id, created_at) VALUES (?, ?, ?) ON CONFLICT(student_id, opportunity_id) DO NOTHING', (student_identity(current_user), real_id, utc_now()))
    db.commit()

    return {
        "success": True,
        "message": "Opportunity saved successfully",
        "opportunity_id": opportunity_id,
        "db_id": real_id,
    }


@app.delete("/api/saved/{opportunity_id}")
def remove_saved_opportunity(
    opportunity_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(db_session),
):
    """Remove an opportunity bookmark for the logged-in student."""
    opp = find_opportunity(db, opportunity_id)
    real_id = opp["id"] if opp else None

    cursor = db.cursor()
    if real_id:
        cursor.execute(
            "DELETE FROM saved_opportunities WHERE user_id = ? AND opportunity_id = ?",
            (current_user["id"], real_id),
        )
    else:
        cursor.execute(
            "DELETE FROM saved_opportunities WHERE user_id = ? AND 1 = 0",
            (current_user["id"],),
        )
    if real_id:
        cursor.execute('DELETE FROM profile_saved WHERE student_id = ? AND opportunity_id = ?', (student_identity(current_user), real_id))
    db.commit()

    return {
        "success": True,
        "message": "Opportunity removed from saved list",
        "opportunity_id": opportunity_id,
    }


@app.get("/api/saved")
def list_saved_opportunities(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(db_session),
):
    """List all opportunities bookmarked by the authenticated student with match scores."""
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT o.* FROM opportunities o
        JOIN saved_opportunities s ON o.id = s.opportunity_id
        WHERE s.user_id = ?
        ORDER BY s.created_at DESC
        """,
        (current_user["id"],),
    )
    rows = cursor.fetchall()
    opps = rows_to_list(rows)

    cursor.execute("SELECT opportunity_id FROM applications WHERE user_id = ?", (current_user["id"],))
    applied_ids = {r[0] for r in cursor.fetchall()}

    for opp in opps:
        opp.update(verification_state(opp))
        public_id = opp.get("slug") or opp["id"]
        opp["db_id"] = opp["id"]
        opp["id"] = public_id
        match_info = calculate_match(get_student_profile(db, student_identity(current_user), current_user), opp)
        opp["match"] = match_info
        opp["match_score"] = match_info["overall"]
        opp["is_saved"] = True
        opp["is_applied"] = opp["db_id"] in applied_ids

    return opps


# ---------------------------------------------------------------------------
# Applications Routes (/api/applications)
# ---------------------------------------------------------------------------
@app.post("/api/applications/{opportunity_id}")
def track_application(
    opportunity_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(db_session),
):
    """Track an applied opportunity for the current student."""
    opp = find_opportunity(db, opportunity_id)
    if not opp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity with ID or slug {opportunity_id} does not exist.",
        )
    real_id = opp["id"]

    cursor = db.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO applications (user_id, opportunity_id, status) VALUES (?, ?, 'applied')",
        (current_user["id"], real_id),
    )
    from application_service import track
    track(db, opportunity_id, student_identity(current_user), 'Applied', None, current_user)
    db.commit()

    return {
        "success": True,
        "message": "Application tracked successfully",
        "opportunity_id": opportunity_id,
        "db_id": real_id,
    }


@app.get("/api/applications")
def list_applications(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: sqlite3.Connection = Depends(db_session),
):
    """List all applications submitted by the current user."""
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT a.id as application_id, a.status, a.created_at as applied_at, o.*
        FROM applications a
        JOIN opportunities o ON a.opportunity_id = o.id
        WHERE a.user_id = ?
        ORDER BY a.created_at DESC
        """,
        (current_user["id"],),
    )
    rows = cursor.fetchall()
    apps = rows_to_list(rows)

    for item in apps:
        item.update(verification_state(item))
        public_id = item.get("slug") or item["id"]
        item["db_id"] = item["id"]
        item["id"] = public_id
        item["match"] = calculate_match(get_student_profile(db, student_identity(current_user), current_user), item)
        item["match_score"] = item["match"]["overall"]
        item["is_applied"] = True

    return apps


# ---------------------------------------------------------------------------
# Dashboard Routes (/api/dashboard/stats, /api/categories, /api/deadlines)
# ---------------------------------------------------------------------------
@app.get("/api/dashboard/stats")
def get_dashboard_stats(
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    db: sqlite3.Connection = Depends(db_session),
):
    """
    Return dashboard stats:
    - match_score: average of top 10 matched opportunities
    - saved_count: count of bookmarked opportunities
    - applied_count: count of applied opportunities
    - deadline_count: opportunities expiring within the next 7 days
    """
    cursor = db.cursor()
    today = today_in_india()

    cursor.execute("SELECT * FROM opportunities WHERE is_verified_active = 1 AND (deadline_iso = '' OR deadline_iso >= ?)", (today_in_india().isoformat(),))
    all_opps = rows_to_list(cursor.fetchall())

    # Average match score of top 10 opportunities
    match_scores = [calculate_match(get_student_profile(db, student_identity(current_user), current_user), opp)["overall"] for opp in all_opps]
    match_scores.sort(reverse=True)
    top_10 = match_scores[:10]
    avg_top_match = round(sum(top_10) / len(top_10), 1) if top_10 else 0.0

    # User saved & applied counts
    saved_ids, applied_ids = workspace_sets(db, current_user)
    saved_count, applied_count = len(saved_ids), len(applied_ids)

    # Deadlines count in next 7 days
    deadline_count = 0
    for opp in all_opps:
        dl_str = opp.get("deadline")
        if dl_str:
            try:
                dl_date = datetime.strptime(dl_str.strip(), "%Y-%m-%d").date()
                diff_days = (dl_date - today).days
                if 0 <= diff_days <= 7:
                    deadline_count += 1
            except (ValueError, TypeError):
                pass

    return {
        "match_score": avg_top_match,
        "saved_count": saved_count,
        "applied_count": applied_count,
        "deadline_count": deadline_count,
    }


@app.get("/api/categories")
def get_categories(db: sqlite3.Connection = Depends(db_session)):
    """Return category counts with icons and display names: [{name, count, emoji}]."""
    category_definitions = [
        {"type": "scholarship", "name": "Scholarships", "emoji": "🎓"},
        {"type": "internship", "name": "Internships", "emoji": "💼"},
        {"type": "competition", "name": "Competitions", "emoji": "🏆"},
        {"type": "free_offer", "name": "Free Offers", "emoji": "🎁"},
        {"type": "event", "name": "Events", "emoji": "📅"},
        {"type": "olympiad", "name": "Olympiads", "emoji": "🥇"},
    ]

    cursor = db.cursor()
    cursor.execute("SELECT type, COUNT(*) as cnt FROM opportunities GROUP BY type")
    counts = {row["type"].lower(): row["cnt"] for row in cursor.fetchall()}

    result = []
    for cat in category_definitions:
        c_type = cat["type"]
        cnt = counts.get(c_type, 0)
        result.append(
            {
                "type": c_type,
                "name": cat["name"],
                "count": cnt,
                "emoji": cat["emoji"],
            }
        )

    return result


@app.get("/api/deadlines")
def get_upcoming_deadlines(
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    db: sqlite3.Connection = Depends(db_session),
):
    """Return opportunities sorted by deadline date with computed days_left."""
    cursor = db.cursor()
    cursor.execute("SELECT * FROM opportunities WHERE deadline IS NOT NULL AND deadline != '' ORDER BY deadline ASC")
    rows = cursor.fetchall()
    opps = rows_to_list(rows)

    today = today_in_india()
    results = []
    for opp in opps:
        dl_str = opp.get("deadline", "")
        days_left = None
        try:
            dl_date = datetime.strptime(dl_str.strip(), "%Y-%m-%d").date()
            days_left = (dl_date - today).days
        except (ValueError, TypeError):
            days_left = 999

        match_info = calculate_match(get_student_profile(db, student_identity(current_user), current_user), opp)
        opp["match"] = match_info
        opp["match_score"] = match_info["overall"]
        opp["days_left"] = days_left
        results.append(opp)

    # Sort primarily by days_left (positive deadlines first, then overdue)
    results.sort(key=lambda x: (x["days_left"] if x["days_left"] is not None and x["days_left"] >= 0 else 9999 + abs(x.get("days_left") or 0)))
    return results


# ---------------------------------------------------------------------------
# Search Route (/api/search)
# ---------------------------------------------------------------------------
@app.get("/api/search")
def search_opportunities(
    q: str = Query("", description="Full text search query"),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    db: sqlite3.Connection = Depends(db_session),
):
    """Full-text search across title, organization, description, and tags."""
    cursor = db.cursor()
    query_str = q.strip().lower()

    if not query_str:
        cursor.execute("SELECT * FROM opportunities ORDER BY is_trending DESC, id ASC")
    else:
        like_pattern = f"%{query_str}%"
        cursor.execute(
            """
            SELECT * FROM opportunities
            WHERE LOWER(title) LIKE ?
               OR LOWER(organization) LIKE ?
               OR LOWER(description) LIKE ?
               OR LOWER(tags) LIKE ?
               OR LOWER(required_skills) LIKE ?
            ORDER BY is_trending DESC
            """,
            (like_pattern, like_pattern, like_pattern, like_pattern, like_pattern),
        )

    opps = [dict(row) for row in cursor.fetchall() if row['is_verified_active'] and (not row['deadline_iso'] or row['deadline_iso'] >= today_in_india().isoformat())]

    saved_ids, applied_ids = workspace_sets(db, current_user)

    for opp in opps:
        opp.update(verification_state(opp))
        match_info = calculate_match(get_student_profile(db, student_identity(current_user), current_user), opp)
        opp["match"] = match_info
        opp["match_score"] = match_info["overall"]
        opp["is_saved"] = opp["id"] in saved_ids
        opp["is_applied"] = opp["id"] in applied_ids

    opps.sort(key=lambda x: x["match_score"], reverse=True)
    return opps


# ---------------------------------------------------------------------------
# Data Integrity & Verification Engine Route (/api/verification)
# ---------------------------------------------------------------------------
@app.get("/api/verification/sample")
def get_verification_sample():
    """Returns real-time verification comparison between messy scraped data and clean verified JSON."""
    return {'mode': 'demo', 'is_simulated': True, 'is_verified': False,
            'message': 'Illustration only. No portal or accuracy measurement was performed.',
            'scraped_data': {'title': 'Example opportunity (simulated)'},
            'verified_data': None, 'transformations': ['Validate the schema', 'Inspect a real application action', 'Record actual evidence']}


class VerifyOpportunityRequest(BaseModel):
    opportunity_id: Optional[str] = "reliance"
    title: Optional[str] = ""
    provider: Optional[str] = ""
    user_profile: Optional[Dict[str, Any]] = None
    live_agent: Optional[bool] = True


@app.post("/api/verify-opportunity", dependencies=[Depends(require_verification_access)])
async def verify_opportunity_endpoint(
    req: VerifyOpportunityRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    db: sqlite3.Connection = Depends(db_session),
):
    """
    Two-Filter Opportunity Verification Engine:
      Filter 1: TinyFish Ingestion (TinySearch -> TinyFetch -> TinyAgent Mako)
      Filter 2: configured Gemini model Structured Validation & Profile Cross-Check
    """
    from verification import verify_and_store
    opp = find_opportunity(db, req.opportunity_id or 'reliance')
    if not opp:
        raise HTTPException(404, 'Opportunity not found.')
    profile = get_student_profile(db, student_identity(current_user), current_user)
    return await verify_and_store(db, opp['title'], opp, live=bool(req.live_agent), profile=profile)


@app.get("/api/verify-opportunity/{opportunity_id}", dependencies=[Depends(require_verification_access)])
async def verify_opportunity_get(
    opportunity_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    db: sqlite3.Connection = Depends(db_session),
):
    """GET shortcut for live opportunity verification."""
    req = VerifyOpportunityRequest(opportunity_id=opportunity_id)
    return await verify_opportunity_endpoint(req, current_user=current_user, db=db)


# ---------------------------------------------------------------------------
# Resume Analyzer Route (/api/resume/analyze)
# ---------------------------------------------------------------------------
@app.post("/api/resume/analyze", dependencies=[Depends(resume_rate_limiter.check)])
async def analyze_resume_endpoint(
    request: Request,
    file: Optional[UploadFile] = File(None),
    use_sample: Optional[bool] = Form(None),
    current_user: Optional[Dict[str, Any]] = Depends(get_workspace_user),
    db: sqlite3.Connection = Depends(db_session),
):
    """
    Analyzes resume (.pdf, .docx, .txt) or sample_resume.txt.
    Enforces a strict 5 MB file size limit and MIME validation with clear HTTP 400/413 errors.
    Structures profile via configured Gemini model (with resilient fallback).
    """
    raw_text = None
    data = None
    filename = "sample_resume.txt"

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            if body.get("text"):
                raw_text = body["text"]
                filename = "pasted_resume.txt"
            elif body.get("use_sample"):
                use_sample = True
        except Exception:
            pass

    if file and not use_sample and not raw_text:
        filename = (file.filename or "uploaded_resume.pdf").replace("\\", "/").split("/")[-1][:180]
        ext = os.path.splitext(filename)[1].lower()
        allowed_extensions = {".pdf", ".docx", ".txt"}
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Please upload a PDF (.pdf), Word (.docx), or plain text (.txt) document.",
            )

        allowed_mimes = {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
            "text/plain",
            "application/octet-stream",
        }
        if file.content_type and file.content_type.lower() not in allowed_mimes and not file.content_type.startswith("text/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported MIME type '{file.content_type}'. Please upload a valid .pdf, .docx, or .txt file.",
            )

        max_bytes = 5 * 1024 * 1024  # 5 MB
        data = await file.read(max_bytes + 1)
        await file.close()
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Uploaded file exceeds the maximum 5 MB limit ({len(data)} bytes).",
            )
    elif not raw_text:
        if not use_sample:
            raise HTTPException(400, 'Choose a resume or explicitly select the demo sample.')
        if mode() != 'demo':
            raise HTTPException(409, 'Sample resumes are available only in demo mode.')
        raw_text = load_sample_resume_text()
    if raw_text is not None and (not isinstance(raw_text, str) or len(raw_text.encode('utf-8')) > 100000):
        raise HTTPException(413, 'Pasted resume text exceeds the 100 KB limit.')

    profile = await analyze_resume_bytes(filename=filename, data=data, raw_text=raw_text)
    identity = student_identity(current_user)
    if raw_text is None and data:
        from resume_analyzer import extract_text_from_bytes
        import asyncio
        raw_text = await asyncio.to_thread(extract_text_from_bytes, filename, data)
    from catalog import utc_now
    saved_profile = save_student_profile(db, identity, {**profile, 'resume_filename': filename, 'resume_uploaded_at': utc_now()}, resume_text=raw_text or '')

    if current_user and db:
        try:
            persisted = persist_profile_to_user(db, current_user["id"], profile)
            profile["user"] = persisted
        except Exception as e:
            raise HTTPException(500, "Your resume profile could not be saved. Please retry.") from None

    return {
        "success": True,
        "profile": profile,
        "student_profile": __import__("frontend_api").profile_payload(saved_profile),
        "is_simulated": bool(use_sample),
        "filename": filename,
    }


# ---------------------------------------------------------------------------
# Dynamic Opportunity Matching Engine Route (/api/opportunities/match)
# ---------------------------------------------------------------------------
class MatchRequest(BaseModel):
    user_profile: Optional[Dict[str, Any]] = None
    opportunity_ids: Optional[List[str]] = None
    category: Optional[str] = None


@app.post("/api/opportunities/match")
async def match_opportunities_endpoint(
    req: MatchRequest = Body(default_factory=MatchRequest),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    db: sqlite3.Connection = Depends(db_session),
):
    """
    Calculates match scores, breakdown percentages, eligibility checklists,
    and policy conflicts against the provided or authenticated student profile.
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM opportunities WHERE is_verified_active = 1 OR is_verified_active IS NULL")
    opps = rows_to_list(cursor.fetchall())

    profile = req.user_profile
    if not profile and current_user:
        profile = get_student_profile(db, student_identity(current_user), current_user)
    if not profile:
        profile = get_student_profile(db, student_identity(current_user), current_user)

    saved_ids = set()
    if current_user:
        s_cursor = db.cursor()
        s_cursor.execute("SELECT opportunity_id FROM saved_opportunities WHERE user_id = ?", (current_user["id"],))
        saved_ids = {r[0] for r in s_cursor.fetchall()}

    opps = [o for o in opps if not o.get('deadline_iso') or o['deadline_iso'] >= today_in_india().isoformat()]
    scored = score_catalog(profile, opps, saved_ids)
    for opp in scored:
        public_id = opp.get("slug") or opp["id"]
        opp["db_id"] = opp["id"]
        opp["id"] = public_id
        opp["is_saved"] = opp["db_id"] in saved_ids
        opp["checklist"] = eligibility_checklist(profile or {}, opp)

    if req.opportunity_ids:
        scored = [o for o in scored if str(o["id"]) in req.opportunity_ids or str(o["db_id"]) in req.opportunity_ids]

    if req.category:
        cat_lower = req.category.lower().strip()
        scored = [
            o for o in scored
            if (o.get("category") or "").lower() == cat_lower
            or (o.get("type") or "").lower() == cat_lower
        ]

    return scored


# ---------------------------------------------------------------------------
# Discovery & Verification Route (/api/opportunities/discover-and-verify)
# ---------------------------------------------------------------------------
class DiscoverVerifyRequest(BaseModel):
    query: Optional[str] = None
    query_or_url: Optional[str] = None
    user_profile: Optional[Dict[str, Any]] = None
    live_agent: Optional[bool] = True


@app.post("/api/opportunities/discover-and-verify", dependencies=[Depends(require_verification_access)])
async def discover_and_verify_endpoint(
    req: DiscoverVerifyRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    db: sqlite3.Connection = Depends(db_session),
):
    """
    Stage A (TinySearch) -> Stage B (TinyFetch) -> Stage C (TinyAgent Mako) -> Filter 2 (configured Gemini model).
    Extracts structured VerifiedOpportunity and upserts into SQLite opportunities table.
    Rate-limited to 10 requests per 10 minutes per IP.
    """
    from verification import verify_and_store
    target = req.query_or_url or req.query or 'Bharti Airtel Scholarship'
    cursor = db.execute('SELECT * FROM opportunities WHERE LOWER(title) LIKE LOWER(?) OR url = ? OR apply_url = ? LIMIT 1', ('%' + target + '%', target, target))
    row = cursor.fetchone()
    profile = get_student_profile(db, student_identity(current_user), current_user)
    return await verify_and_store(db, target, dict(row) if row else None, live=bool(req.live_agent), profile=profile)


# ---------------------------------------------------------------------------
# AI Assistant Route (/api/assistant/chat)
# ---------------------------------------------------------------------------
class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: Optional[List[Dict[str, str]]] = []
    student_profile: Optional[Dict[str, Any]] = None
    active_opportunity_id: Optional[str] = None


@app.post("/api/assistant/chat", dependencies=[Depends(chat_rate_limiter.check)])
async def assistant_chat_endpoint(
    req: AssistantChatRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
    db: sqlite3.Connection = Depends(db_session),
):
    result = await process_assistant_chat(
        message=req.message,
        history=req.history,
        student_profile=req.student_profile,
        active_opportunity_id=req.active_opportunity_id,
        db=db,
        current_user=current_user,
    )
    return result


# ---------------------------------------------------------------------------
# Calendar Feeds & Notifications (/api/opportunities/{id}/ics, /api/users/{id}/calendar.ics)
# ---------------------------------------------------------------------------
@app.get("/api/opportunities/{opportunity_id}/ics")
def generate_opportunity_ics(
    opportunity_id: str,
    db: sqlite3.Connection = Depends(db_session),
):
    """
    Generates a valid RFC 5545 iCalendar (.ics) file using the opportunity's real deadline date
    with -PT72H (3-day) and -PT24H (1-day) VALARM reminders.
    """
    opp = find_opportunity(db, opportunity_id)
    if not opp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity {opportunity_id} not found."
        )

    from application_service import calendar_event
    return Response(calendar_event(opp), media_type='text/calendar', headers={'Content-Disposition': 'attachment; filename="iris-deadline.ics"'})


@app.get("/api/users/{user_id}/calendar.ics")
def generate_user_calendar_ics(user_id: int, current_user=Depends(get_current_user), db=Depends(db_session)):
    if user_id != current_user['id']:
        raise HTTPException(403, 'This calendar belongs to another account.')
    from application_service import calendar_event
    records = db.execute('SELECT o.* FROM opportunities o JOIN saved_opportunities s ON s.opportunity_id = o.id WHERE s.user_id = ?', (user_id,)).fetchall()
    events = []
    for row in records:
        try:
            data = calendar_event(dict(row))
            events.append('BEGIN:VEVENT' + data.split('BEGIN:VEVENT', 1)[1].split('END:VEVENT', 1)[0] + 'END:VEVENT\r\n')
        except HTTPException:
            continue
    content = 'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//IRIS onE//Saved deadlines//EN\r\n' + ''.join(events) + 'END:VCALENDAR\r\n'
    return Response(content, media_type='text/calendar', headers={'Content-Disposition': 'attachment; filename="iris-saved-deadlines.ics"'})


# ---------------------------------------------------------------------------
# Telegram Deadline Alerts (/api/notifications/telegram-test)
# ---------------------------------------------------------------------------
class TelegramAlertRequest(BaseModel):
    chat_id: Optional[str] = None
    message: Optional[str] = None
    opportunity_id: Optional[str] = None
    preview: bool = True


@app.post("/api/notifications/telegram-test", dependencies=[Depends(chat_rate_limiter.check)])
async def send_telegram_alert(req: TelegramAlertRequest = Body(default_factory=TelegramAlertRequest), current_user=Depends(get_current_user), db=Depends(db_session)):
    chat_id = current_user.get('telegram_chat_id')
    if req.chat_id and req.chat_id != chat_id:
        raise HTTPException(403, 'Use the recipient configured on your own profile.')
    text = (req.message or 'IRIS onE reminder test. Check your tracked application deadlines.')[:2000]
    key = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    if req.preview or mode() == 'demo' or not key or not chat_id:
        return {'success': False, 'delivered': False, 'mode': 'preview', 'preview': text, 'message': 'Preview only; no notification was sent.'}
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(f'https://api.telegram.org/bot{key}/sendMessage', json={'chat_id': chat_id, 'text': text})
            response.raise_for_status()
            data = response.json()
            if not data.get('ok'):
                raise ValueError('Notification rejected')
        return {'success': True, 'delivered': True, 'mode': 'live'}
    except Exception as exc:
        from diagnostics import record
        record('Telegram', 'LIVE_FAILED', error=exc)
        raise HTTPException(502, 'The notification could not be delivered.') from None


# ---------------------------------------------------------------------------
# Static Files & Frontend Mount
# ---------------------------------------------------------------------------
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
parent_mvp_html = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "iris-one-mvp.html"))

if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
elif os.path.isfile(parent_mvp_html):
    @app.get("/", include_in_schema=False)
    def serve_frontend_mvp():
        return FileResponse(parent_mvp_html)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
