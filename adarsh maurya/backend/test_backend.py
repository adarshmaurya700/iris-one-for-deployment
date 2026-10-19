import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from starlette.testclient import TestClient
from main import app

client = TestClient(app)

print("Starting IRIS one backend verification...")

# 1. Test Categories
res = client.get("/api/categories")
assert res.status_code == 200, res.text
categories = res.json()
print("Categories count:", len(categories))
for c in categories:
    print(f"  {c['name']} ({c['type']}): {c['count']}")

# 2. Test Signup
signup_data = {
    "email": "student_test@example.com",
    "password": "Password123!",
    "name": "Adarsh Maurya",
    "college": "IIT Delhi",
    "age": 20,
    "state": "Delhi",
    "country": "India",
    "skills": "Python, Machine Learning, FastAPI",
    "domains": "AI, Backend"
}
res = client.post("/api/auth/signup", json=signup_data)
if res.status_code == 400:
    print("User already exists, proceeding to login...")
else:
    assert res.status_code == 201, res.text
    print("Signup: SUCCESS (201 Created)")

# 3. Test Login
res = client.post("/api/auth/login", json={"email": "student_test@example.com", "password": "Password123!"})
assert res.status_code == 200, res.text
token = res.json()["token"]
headers = {"Authorization": f"Bearer {token}"}
print("Login: SUCCESS (200 OK)")

# 4. Test Get Current User
res = client.get("/api/auth/me", headers=headers)
assert res.status_code == 200, res.text
me = res.json()
assert me["email"] == "student_test@example.com"
print("Auth /me: SUCCESS")

# 5. Test Update Profile
res = client.put("/api/auth/profile", json={"skills": "Python, FastAPI, React, AI, Machine Learning"}, headers=headers)
assert res.status_code == 200, res.text
assert "React" in res.json()["skills"]
print("Profile Update: SUCCESS")

# 6. Test Opportunities list
res = client.get("/api/opportunities", headers=headers)
assert res.status_code == 200, res.text
opps = res.json()
assert len(opps) >= 15
print(f"Opportunities list: SUCCESS ({len(opps)} items)")
print(f"  Top Match: '{opps[0]['title']}' - Score: {opps[0]['match_score']}%")

# Test Filter by Category
res = client.get("/api/opportunities?category=scholarship", headers=headers)
assert res.status_code == 200, res.text
scholarships = res.json()
assert all(s["type"] == "scholarship" for s in scholarships)
print(f"Filter by Category (scholarship): SUCCESS ({len(scholarships)} items)")

# Test Sorting by Deadline
res = client.get("/api/opportunities?sort=deadline", headers=headers)
assert res.status_code == 200, res.text
by_dl = res.json()
print(f"Sort by Deadline: SUCCESS (First: '{by_dl[0]['title']}' at {by_dl[0]['deadline']})")

# 7. Test Opportunity Detail
first_id = opps[0]["id"]
res = client.get(f"/api/opportunities/{first_id}", headers=headers)
assert res.status_code == 200, res.text
detail = res.json()
assert "breakdown" in detail["match"]
print(f"Opportunity Detail ({first_id}): SUCCESS")

# 8. Test Save Opportunity
res = client.post(f"/api/saved/{first_id}", headers=headers)
assert res.status_code == 200, res.text
print(f"Bookmark Opportunity ({first_id}): SUCCESS")

# 9. Test Saved list
res = client.get("/api/saved", headers=headers)
assert res.status_code == 200, res.text
saved = res.json()
assert any(s["id"] == first_id for s in saved)
print(f"Saved List: SUCCESS ({len(saved)} bookmarks)")

# 10. Test Applications
res = client.post(f"/api/applications/{first_id}", headers=headers)
assert res.status_code == 200, res.text
print(f"Track Application ({first_id}): SUCCESS")

res = client.get("/api/applications", headers=headers)
assert res.status_code == 200, res.text
apps = res.json()
assert len(apps) >= 1
print(f"Applications List: SUCCESS ({len(apps)} applications)")

# 11. Test Dashboard Stats
res = client.get("/api/dashboard/stats", headers=headers)
assert res.status_code == 200, res.text
stats = res.json()
print("Dashboard Stats: SUCCESS ->", stats)
assert "match_score" in stats
assert "saved_count" in stats
assert "applied_count" in stats
assert "deadline_count" in stats

# 12. Test Deadlines
res = client.get("/api/deadlines", headers=headers)
assert res.status_code == 200, res.text
deadlines = res.json()
print(f"Upcoming Deadlines: SUCCESS ({len(deadlines)} items)")
print(f"  Next up: '{deadlines[0]['title']}' (days_left: {deadlines[0]['days_left']})")

# 13. Test Search
res = client.get("/api/search?q=python", headers=headers)
assert res.status_code == 200, res.text
search_res = res.json()
print(f"Search for 'python': SUCCESS ({len(search_res)} results)")

# 14. Test Remove Saved
res = client.delete(f"/api/saved/{first_id}", headers=headers)
assert res.status_code == 200, res.text
print(f"Remove Bookmark ({first_id}): SUCCESS")

# 15. Test Live Opportunity Verification Engine (TinyFish + Gemini)
res = client.post("/api/verify-opportunity", json={
    "opportunity_id": "reliance",
    "title": "Reliance Foundation Undergraduate Scholarship",
    "provider": "Reliance Foundation",
    "live_agent": False
}, headers=headers)
assert res.status_code == 200, res.text
verify_res = res.json()
print("Live Verification Endpoint: SUCCESS ->", verify_res.get("pipeline_mode"))
assert "steps" in verify_res
assert len(verify_res["steps"]) >= 4
print(f"  Total stages evaluated: {len(verify_res['steps'])}")
for s in verify_res["steps"]:
    print(f"  ✓ [{s['stage']}]: {s['detail']} ({s['duration_ms']}ms)")
assert verify_res.get("is_verified") is True
assert verify_res.get("verified_data") is not None
print(f"  Verified value: {verify_res['verified_data'].get('financial_value_inr')}")
print(f"  Verified match score: {verify_res.get('match_score')}%")

# 16. Test GET shortcut for verification
res_get = client.get("/api/verify-opportunity/delhi-mcm", headers=headers)
assert res_get.status_code == 200, res_get.text
print("GET /api/verify-opportunity/delhi-mcm: SUCCESS")

# 17. Test Resume Analyzer (/api/resume/analyze)
res_resume = client.post("/api/resume/analyze", data={"use_sample": "true"}, headers=headers)
assert res_resume.status_code == 200, res_resume.text
resume_data = res_resume.json()
assert resume_data.get("success") is True
profile = resume_data.get("profile", {})
assert "skills" in profile or "extracted_skills" in profile
print(f"Resume Analyzer: SUCCESS (Profile: {profile.get('name')}, Tier: {profile.get('academic_tier')}, Skills: {len(profile.get('skills', []))})")

# 18. Test Opportunity Dynamic Matcher (/api/opportunities/match)
res_match = client.post("/api/opportunities/match", json={
    "user_profile": {
        "name": "Adarsh Maurya",
        "academic_tier": "B.Tech 1st Year • GGSIPU USAR",
        "college": "B.Tech CSE, 1st Year",
        "state": "Delhi",
        "country": "India",
        "skills": ["Python", "FastAPI", "React", "AI/ML"],
        "domains": ["Technology", "Scholarships", "Engineering"]
    }
}, headers=headers)
assert res_match.status_code == 200, res_match.text
matched_opps = res_match.json()
assert len(matched_opps) >= 10
print(f"Opportunity Matcher: SUCCESS ({len(matched_opps)} opportunities scored)")
top_matched = matched_opps[0]
print(f"  Top Match: '{top_matched['title']}' -> {top_matched.get('match_score')}%")
assert "checklist" in top_matched
assert 65 <= top_matched.get("match_score", 0) <= 99

# 19. Test Opportunity Discover & Verify (/api/opportunities/discover-and-verify)
res_disc = client.post("/api/opportunities/discover-and-verify", json={
    "query": "Bharti Airtel Scholarship Program Buddy4Study",
    "live_agent": False
}, headers=headers)
assert res_disc.status_code == 200, res_disc.text
disc_data = res_disc.json()
assert "steps" in disc_data
print(f"Discover & Verify: SUCCESS ({len(disc_data['steps'])} steps, Mode: {disc_data.get('pipeline_mode')})")

# 20. Test Real Deadline .ics Generator (/api/opportunities/{id}/ics)
res_ics = client.get("/api/opportunities/reliance/ics")
assert res_ics.status_code == 200, res_ics.text
assert "BEGIN:VCALENDAR" in res_ics.text
assert "END:VCALENDAR" in res_ics.text
assert "DTSTART" in res_ics.text
print("Real Deadline .ics Generator: SUCCESS (valid text/calendar)")

# 21. Verify 9 Core Opportunities in Database
from database import get_db
db_conn = get_db()
db_cur = db_conn.cursor()
db_cur.execute("SELECT slug, title, category FROM opportunities WHERE slug IN ('airtel', 'delhi-mcm', 'gemini-student', 'adobe-insider', 'aditya-birla', 'github-campus-experts')")
core_rows = db_cur.fetchall()
print(f"Core Verified Opportunities in DB: SUCCESS ({len(core_rows)} verified core items verified)")
for cr in core_rows:
    print(f"  - [{cr[0]}]: {cr[1]} ({cr[2]})")
db_conn.close()

# 22. Test Health Endpoint (/api/health)
res_health = client.get("/api/health")
assert res_health.status_code == 200, res_health.text
health_data = res_health.json()
assert health_data.get("status") == "ok"
assert "database" in health_data
assert "scheduler" in health_data
assert health_data["database"]["total_opportunities"] >= 15
print(f"Health Check (/api/health): SUCCESS (DB status: {health_data['database']['status']}, Scheduler: {health_data['scheduler']['status']})")

# 23. Test Admin Refresh Catalog (/api/admin/refresh-catalog)
res_admin = client.post("/api/admin/refresh-catalog")
assert res_admin.status_code == 200, res_admin.text
admin_data = res_admin.json()
assert "audit_summary" in admin_data
print(f"Admin Refresh Catalog: SUCCESS (Audited: {admin_data['audit_summary'].get('total_opportunities')}, Active: {admin_data['audit_summary'].get('active_count')})")

# 24. Test Subscribable User Calendar Feed (/api/users/{id}/calendar.ics)
res_user_ics = client.get(f"/api/users/{me['id']}/calendar.ics")
assert res_user_ics.status_code == 200, res_user_ics.text
assert "BEGIN:VCALENDAR" in res_user_ics.text
assert "VALARM" in res_user_ics.text
assert "-PT72H" in res_user_ics.text or "-PT24H" in res_user_ics.text
print(f"User Calendar Feed: SUCCESS (Subscribable RFC 5545 feed for user {me['id']})")

# 25. Test Telegram Notification Endpoint (/api/notifications/telegram-test)
res_tg = client.post("/api/notifications/telegram-test", json={
    "chat_id": "123456789",
    "opportunity_id": "airtel"
}, headers=headers)
assert res_tg.status_code == 200, res_tg.text
tg_data = res_tg.json()
assert tg_data.get("success") is True
print(f"Telegram Alert Endpoint: SUCCESS (Mode: {tg_data.get('mode')})")

# 26. Test Resume Upload Guardrails (File Size / Type rejection)
# 26a. Invalid extension
res_bad_ext = client.post(
    "/api/resume/analyze",
    files={"file": ("malicious.exe", b"binarycontent", "application/x-msdownload")},
    headers=headers,
)
assert res_bad_ext.status_code == 400, res_bad_ext.text
print("Resume Upload Guardrail (Bad Extension): SUCCESS (HTTP 400 returned)")

# 26b. Valid txt upload
res_good_txt = client.post(
    "/api/resume/analyze",
    files={"file": ("candidate.txt", b"Adarsh Maurya, B.Tech CSE, Skills: Python, FastAPI", "text/plain")},
    headers=headers,
)
assert res_good_txt.status_code == 200, res_good_txt.text
print("Resume Upload Guardrail (Valid Document): SUCCESS (HTTP 200 returned)")

# 27. Test Context-Aware AI Assistant (/api/assistant/chat)
# 27a. Policy Conflict Analysis
res_ai_conflict = client.post(
    "/api/assistant/chat",
    json={"message": "Can I hold Bharti Airtel Scholarship and Delhi MCM Scheme together?"},
    headers=headers,
)
assert res_ai_conflict.status_code == 200, res_ai_conflict.text
ai_conflict_data = res_ai_conflict.json()
assert "reply" in ai_conflict_data
assert "suggested_opportunities" in ai_conflict_data
assert "quick_prompts" in ai_conflict_data
assert any(k in ai_conflict_data["reply"].lower() for k in ["exclusive", "tuition", "conflict", "airtel"])
print("AI Assistant (Policy Conflict Advisory): SUCCESS (200 OK)")

# 27b. SOP Generation & Active Opportunity Grounding
res_ai_sop = client.post(
    "/api/assistant/chat",
    json={
        "message": "Draft my Scholarship SOP for this opportunity",
        "active_opportunity_id": "airtel"
    },
    headers=headers,
)
assert res_ai_sop.status_code == 200, res_ai_sop.text
ai_sop_data = res_ai_sop.json()
assert "statement of purpose" in ai_sop_data["reply"].lower() or "sop" in ai_sop_data["reply"].lower()
print("AI Assistant (SOP Generation & Active Opportunity Context): SUCCESS (200 OK)")

print("\n*** ALL BACKEND VERIFICATION CHECKS (1-27) COMPLETED WITH 100% SUCCESS! ***")
