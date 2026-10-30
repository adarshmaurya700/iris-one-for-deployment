"""Run: python -B -m unittest discover -s backend -p test_backend.py -v.

Every test uses a disposable database. Provider calls are mocked, never billed.
"""
import asyncio
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault('IRIS_DISABLE_SCHEDULER', '1')
from fastapi.testclient import TestClient
from main import app, ai_rate_limiter, resume_rate_limiter
import database
from database import get_db, init_db, find_opportunity
from application_service import DEMO_PROFILE, save_student_profile, calendar_event
from matcher import compute_deterministic_embedding, evaluate_match_and_conflicts
from scheduler import run_12h_verification_sync
from seed_data import seed_opportunities
from verification import verify_catalog_record


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.connections = []
        self.tmp = tempfile.TemporaryDirectory(prefix='iris-test-')
        self.env = patch.dict(os.environ, {'DATABASE_PATH': str(Path(self.tmp.name) / 'test.db'), 'DATABASE_URL': '',
            'IRIS_DISABLE_SCHEDULER': '1', 'GEMINI_API_KEY': '', 'GROQ_API_KEY': '', 'OLLAMA_BASE_URL': '', 'TINYFISH_API_KEY': ''})
        self.env.start()
        database._postgres_available = None
        ai_rate_limiter.hits.clear()
        resume_rate_limiter.hits.clear()
        self.client = TestClient(app).__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        for connection in self.connections:
            connection.close()
        self.env.stop()
        self.tmp.cleanup()

    def db(self):
        db = get_db()
        self.connections.append(db)
        return db

    def signup(self, email='student@example.test'):
        response = self.client.post('/api/auth/signup', json={'email': email, 'password': 'Password123!', 'name': 'Test Student', 'college': 'B.Tech', 'state': 'Delhi'})
        self.assertEqual(response.status_code, 201, response.text)
        return {'Authorization': 'Bearer ' + response.json()['token']}

    def test_schema_migration_wal_and_idempotent_seed(self):
        db = self.db()
        self.assertEqual(db.execute('PRAGMA journal_mode').fetchone()[0], 'wal')
        count = db.execute('SELECT COUNT(*) FROM opportunities').fetchone()[0]
        db.execute("UPDATE opportunities SET title = 'Live edit', verification_status = 'VERIFIED_LIVE' WHERE slug = 'airtel'")
        db.commit()
        seed_opportunities(db)
        init_db()
        self.assertEqual(db.execute('SELECT COUNT(*) FROM opportunities').fetchone()[0], count)
        self.assertEqual(find_opportunity(db, 'airtel')['title'], 'Live edit')
        for table in ['student_profiles', 'tracked_applications', 'sync_runs']:
            self.assertIsNotNone(db.execute('SELECT name FROM sqlite_master WHERE name = ?', (table,)).fetchone())

    def test_how_to_apply_contract_and_seed_provenance(self):
        for slug in ['airtel', 'delhi-mcm', 'adobe-insider', 'gemini-student', 'aditya-birla', 'reliance', 'microsoft-learn-ambassador', 'google-cloud-credits', 'github-campus-experts', 'jai-2026']:
            with self.subTest(slug=slug):
                response = self.client.get(f'/api/opportunities/{slug}/how-to-apply')
                self.assertEqual(response.status_code, 200, response.text)
                data = response.json()
                self.assertTrue(data['application_channels'])
                self.assertTrue(data['required_documents'])
                self.assertEqual([s['step'] for s in data['how_to_apply_steps']], list(range(1, len(data['how_to_apply_steps']) + 1)))
                self.assertFalse(any(channel['verified'] for channel in data['application_channels']))
                self.assertFalse(data['last_verified_at'])
        self.assertEqual(self.client.get('/api/opportunities/missing/how-to-apply').status_code, 404)

    def test_tracking_persists_checklist_and_detects_conflicts(self):
        guide = self.client.get('/api/opportunities/airtel/how-to-apply').json()
        documents = guide['required_documents'][:2]
        for _ in range(2):
            result = self.client.post('/api/applications/track', json={'opportunity_id': 'airtel', 'checked_documents': documents}).json()
            self.assertEqual(result['tracked_count'], 1)
        data = self.client.get('/api/opportunities/airtel/how-to-apply').json()
        self.assertEqual(data['checked_documents'], documents)
        self.assertEqual(data['tracking_status'], 'In Progress')
        mcm = self.client.get('/api/opportunities/delhi-mcm/how-to-apply').json()
        self.assertIn('Bharti', mcm['conflict_warning'])
        perk = self.client.get('/api/opportunities/gemini-student/how-to-apply').json()
        self.assertIsNone(perk['conflict_warning'])
        self.client.post('/api/applications/track', json={'opportunity_id': 'airtel', 'status': 'Saved'})
        self.assertIsNone(self.client.get('/api/opportunities/delhi-mcm/how-to-apply').json()['conflict_warning'])

    def test_profile_and_tracking_account_isolation(self):
        first = self.signup()
        second = self.signup('second@example.test')
        self.assertEqual(self.client.post('/api/applications/track', json={'opportunity_id': 'airtel'}, headers=first).status_code, 200)
        self.assertEqual(self.client.get('/api/applications/tracked', headers=second).json(), [])
        self.assertEqual(self.client.get('/api/opportunities/airtel/how-to-apply?student_id=user:1', headers=second).status_code, 403)
        self.assertEqual(self.client.get('/api/opportunities/airtel/how-to-apply?student_id=user:1').status_code, 401)
        self.assertEqual(self.client.post('/api/applications/track', json={'opportunity_id': 'airtel', 'status': 'arbitrary'}).status_code, 422)

    def test_rag_answers_from_rows_without_network(self):
        db = self.db()
        db.execute("UPDATE opportunities SET benefit_summary = 'Unique stored benefit marker' WHERE slug = 'airtel'")
        db.commit()
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as network:
            result = self.client.post('/api/assistant/ask', json={'query': 'How do I apply for Bharti Airtel and combine it with Delhi MCM and Google Gemini?'}).json()
            network.assert_not_called()
        self.assertEqual(result['model_used'], 'deterministic-local-rag')
        self.assertLessEqual(len(result['matched_opportunities']), 5)
        self.assertIn('Unique stored benefit marker', result['answer'])
        self.assertIn('5. **Review and submit**', result['answer'])
        self.assertIn('exclusive tuition', result['answer'])
        self.assertIn('stackable', result['answer'])
        self.assertTrue(result['policy_conflicts'])
        self.assertEqual(result['matched_opportunities'][0]['slug'], 'airtel')
        self.assertIn('12h Auto-Sync', result['data_source'])

    def test_model_outage_falls_back(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test', 'GROQ_API_KEY': 'test', 'OLLAMA_BASE_URL': 'http://localhost:11434'}), patch('httpx.AsyncClient.post', new=AsyncMock(side_effect=TimeoutError('offline'))):
            response = self.client.post('/api/assistant/ask', json={'query': 'Airtel documents'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['model_used'], 'deterministic-local-rag')

    def test_local_model_receives_retrieved_context(self):
        import httpx
        response = httpx.Response(200, json={'message': {'content': 'Answer from the supplied context.'}}, request=httpx.Request('POST', 'http://localhost/api/chat'))
        with patch.dict(os.environ, {'OLLAMA_BASE_URL': 'http://localhost:11434'}), patch('httpx.AsyncClient.post', new=AsyncMock(return_value=response)) as model:
            result = self.client.post('/api/assistant/ask', json={'query': 'Airtel documents'}).json()
        self.assertEqual(result['model_used'], 'ollama')
        context = model.call_args.kwargs['json']['messages'][0]['content']
        self.assertIn('how_to_apply_steps_json', context)
        self.assertIn('tracked_applications', context)

    def test_sync_status_trigger_and_honest_offline_trace(self):
        result = self.client.post('/api/sync/trigger', json={'live': False})
        self.assertEqual(result.status_code, 202)
        status = self.client.get('/api/sync/status').json()
        self.assertEqual(status['cron_interval_hours'], 12)
        self.assertTrue(status['last_sync_iso'])
        self.assertGreater(status['seconds_until_next_run'], 43000)
        self.assertEqual(status['last_result']['mode'], 'cache_only')
        record = find_opportunity(self.db(), 'airtel')
        self.assertTrue(record['last_checked_at'])
        self.assertFalse(record['last_verified_at'])
        trace = json.loads(record['verification_log_json'])
        self.assertEqual(len(trace), 4)
        self.assertTrue(all(step['status'] == 'skipped' for step in trace))
        self.assertEqual(record['verification_status'], 'EXPIRED')
        self.assertNotIn('airtel', [opp['id'] for opp in self.client.get('/api/opportunities').json()])

    def test_sync_lease_rejects_another_worker(self):
        db = self.db()
        db.execute("INSERT INTO worker_locks (name, owner, expires_at) VALUES ('catalog-sync', 'other-process', '9999-01-01T00:00:00Z')")
        db.commit()
        self.assertEqual(run_12h_verification_sync(live=False)['status'], 'already_running')
        self.assertEqual(db.execute('SELECT COUNT(*) FROM sync_runs').fetchone()[0], 0)

    def test_scheduler_starts_with_twelve_hour_job_and_stops(self):
        import scheduler
        from datetime import datetime, timezone
        from catalog import utc_now
        db = self.db()
        db.execute('INSERT INTO sync_runs (run_type, status, executed_at, completed_at) VALUES (?, ?, ?, ?)', ('12H_SCHEDULED_SYNC', 'completed', utc_now(), utc_now()))
        db.commit()
        with patch.dict(os.environ, {'IRIS_DISABLE_SCHEDULER': '0'}):
            try:
                scheduler.start_scheduler()
                self.assertTrue(scheduler._scheduler.running)
                job = scheduler._scheduler.get_job('catalog-verification')
                self.assertEqual(job.trigger.interval.total_seconds(), 43200)
                self.assertGreater((job.next_run_time - datetime.now(timezone.utc)).total_seconds(), 43000)
            finally:
                scheduler.stop_scheduler()
        self.assertIsNone(scheduler._scheduler)

    def test_live_verification_validates_schema_and_open_button(self):
        import httpx
        payload = {'title': 'Verified test scholarship', 'provider': 'Test foundation', 'apply_url': 'https://example.org/apply', 'deadline_iso': '2099-12-31', 'income_cap_inr': 800000, 'min_marks_pct': 60, 'nirf_cutoff': 50, 'is_exclusive_tuition_grant': True, 'how_to_apply_steps': [{'step': 1, 'title': 'Register', 'detail': 'Complete the official form.'}], 'required_documents': ['Student ID']}
        response = httpx.Response(200, json={'candidates': [{'content': {'parts': [{'text': json.dumps(payload)}]}}]}, request=httpx.Request('POST', 'https://example.org'))
        with patch('tinyfish_pipeline._get_api_key', return_value='test'), patch('tinyfish_pipeline._call_tinyfish_search', new=AsyncMock(return_value={'results': []})), patch('tinyfish_pipeline._call_tinyfish_fetch', new=AsyncMock(return_value={'markdown': 'Program details'})), patch('tinyfish_pipeline._call_tinyfish_agent', new=AsyncMock(return_value={'result': {'is_button_live': True}})), patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), patch('httpx.AsyncClient.post', new=AsyncMock(return_value=response)):
            result = asyncio.run(verify_catalog_record({'title': 'Test', 'apply_url': 'https://example.org/apply'}))
        self.assertEqual(result['verification_status'], 'VERIFIED_LIVE')
        self.assertTrue(result['last_verified_at'])
        self.assertEqual(result['fields']['max_family_income_inr'], 800000)
        self.assertEqual([step['status'] for step in result['trace']], ['completed'] * 4)

    def test_live_failure_and_closed_portal_do_not_become_verified(self):
        with patch('tinyfish_pipeline._get_api_key', return_value='test'), patch('tinyfish_pipeline._call_tinyfish_search', new=AsyncMock(side_effect=TimeoutError())):
            failed = asyncio.run(verify_catalog_record({'title': 'Test'}))
        self.assertEqual(failed['verification_status'], 'CACHE_ONLY')
        self.assertFalse(failed['last_verified_at'])
        self.assertEqual(len(failed['trace']), 4)
        with patch('tinyfish_pipeline._get_api_key', return_value='test'), patch('tinyfish_pipeline._call_tinyfish_search', new=AsyncMock(return_value={})), patch('tinyfish_pipeline._call_tinyfish_fetch', new=AsyncMock(return_value={})), patch('tinyfish_pipeline._call_tinyfish_agent', new=AsyncMock(return_value={'result': {'is_button_live': False}})):
            closed = asyncio.run(verify_catalog_record({'title': 'Test', 'url': 'https://example.org'}))
        self.assertEqual(closed['verification_status'], 'CLOSED')
        self.assertFalse(closed['last_verified_at'])

    def test_matching_hard_gates_and_sponsorship(self):
        db = self.db()
        opp = find_opportunity(db, 'airtel')
        profile = {**DEMO_PROFILE, 'nirf_top_50': 1}
        good = evaluate_match_and_conflicts(profile, opp, [])
        self.assertTrue(good['eligible'])
        bad = evaluate_match_and_conflicts({**profile, 'family_income_inr': 900000, 'class_12_pct': 40, 'nirf_top_50': 0}, opp, [])
        self.assertFalse(bad['eligible'])
        self.assertLess(bad['match_score'], good['match_score'])
        self.assertEqual(len(bad['gate_warnings']), 3)
        db.execute("UPDATE opportunities SET is_sponsored = 1 WHERE slug = 'reliance'")
        db.commit()
        data = self.client.get('/api/opportunities').json()
        self.assertTrue(all(not row['is_sponsored'] or (row['match_score'] >= 85 and row['match']['eligible']) for row in data))

    def test_embeddings_stable_across_processes(self):
        code = 'import json; from matcher import compute_deterministic_embedding as e; print(json.dumps(e("Python FastAPI Delhi")))'
        result = subprocess.check_output([sys.executable, '-B', '-c', code], cwd=Path(__file__).parent, text=True)
        self.assertEqual(json.loads(result), compute_deterministic_embedding('Python FastAPI Delhi'))

    def test_calendar_escaping_folding_and_reminders(self):
        response = self.client.get('/api/opportunities/reliance/calendar.ics')
        self.assertEqual(response.status_code, 200)
        data = response.content
        self.assertIn(b'TRIGGER:-PT72H\r\n', data)
        self.assertIn(b'TRIGGER:-PT24H\r\n', data)
        self.assertNotIn(b'\r\r\n', data)
        self.assertTrue(all(len(line) <= 75 for line in data.split(b'\r\n')))
        event = calendar_event({'id': 1, 'title': 'A;B, C\nInjected: text ' + '₹'*50, 'deadline_iso': '2099-01-01', 'url': 'https://example.org'})
        self.assertIn('A\\;B\\, C\\nInjected', event)
        self.assertEqual(self.client.get('/api/opportunities/gemini-student/calendar.ics').status_code, 409)

    def test_auth_saved_dashboard_and_legacy_chat_routes(self):
        headers = self.signup()
        self.assertEqual(self.client.get('/api/auth/me', headers=headers).status_code, 200)
        self.assertEqual(self.client.post('/api/saved/reliance', headers=headers).status_code, 200)
        self.assertTrue(self.client.get('/api/saved', headers=headers).json())
        self.assertEqual(self.client.post('/api/applications/reliance', headers=headers).status_code, 200)
        self.assertEqual(self.client.get('/api/dashboard/stats', headers=headers).status_code, 200)
        self.assertEqual(self.client.post('/api/assistant/chat', json={'message': 'Airtel SOP'}, headers=headers).status_code, 200)
        self.assertEqual(self.client.get('/api/health').json()['status'], 'ok')

    def test_resume_formats_persist_profile_for_rag(self):
        headers = self.signup()
        text = b'Test Student\nB.Tech CSE Delhi\nSkills: Python FastAPI React'
        result = self.client.post('/api/resume/analyze', files={'file': ('resume.txt', text, 'text/plain')}, headers=headers)
        self.assertEqual(result.status_code, 200, result.text)
        row = self.db().execute("SELECT * FROM student_profiles WHERE id = 'user:1'").fetchone()
        self.assertIn('Test Student', row['resume_text'])
        self.assertTrue(json.loads(row['skills_json']))
        self.assertEqual(self.client.post('/api/resume/analyze', files={'file': ('bad.exe', b'bad')}, headers=headers).status_code, 400)
        from resume_analyzer import extract_text_from_bytes
        from docx import Document
        document = Document()
        document.add_paragraph('DOCX resume: Python')
        buffer = io.BytesIO()
        document.save(buffer)
        self.assertIn('Python', extract_text_from_bytes('resume.docx', buffer.getvalue()))
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        buffer = io.BytesIO()
        writer.write(buffer)
        self.assertEqual(extract_text_from_bytes('resume.pdf', buffer.getvalue()), '')

    def test_discovery_offline_returns_trace_without_inserting_fake_record(self):
        before = self.db().execute('SELECT COUNT(*) FROM opportunities').fetchone()[0]
        response = self.client.post('/api/opportunities/discover-and-verify', json={'query': 'Unknown opportunity', 'live_agent': False})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['steps']), 4)
        self.assertFalse(response.json()['is_verified'])
        self.assertEqual(self.db().execute('SELECT COUNT(*) FROM opportunities').fetchone()[0], before)

    def test_unavailable_postgres_falls_back_to_sqlite(self):
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://invalid:invalid@127.0.0.1:1/iris'}):
            db = get_db()
            try:
                self.assertIsInstance(db, __import__('sqlite3').Connection)
                self.assertFalse(database._postgres_available)
                self.assertNotIn('postgres', database.get_db_path())
            finally:
                db.close()

    def test_onboarding_profile_alias_persists_and_clears_fields(self):
        headers = self.signup()
        values = {'name': 'A Student', 'age': 19, 'academic_stage': 'B.Tech (1st Year)', 'institution': 'GGSIPU USAR', 'graduation_year': 2028, 'country': 'India', 'state_domicile': 'Delhi', 'skills': ['Python', 'React'], 'domains': ['Scholarships', 'Hackathons'], 'onboarding_complete': True, 'preferences': {'reduce_motion': True}}
        response = self.client.post('/api/profile/update', json=values, headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        profile = self.client.get('/api/profile', headers=headers).json()
        self.assertEqual(profile['institution'], 'GGSIPU USAR')
        self.assertEqual(profile['graduation_year'], 2028)
        self.assertEqual(profile['domains'], ['Scholarships', 'Hackathons'])
        self.assertTrue(profile['preferences']['reduce_motion'])
        self.assertEqual(profile['onboarding_complete'], 1)
        self.assertNotIn('resume_text', profile)
        self.assertNotIn('embedding_json', profile)
        self.assertEqual(self.client.get('/api/auth/me', headers=headers).json()['name'], 'A Student')
        cleared = self.client.post('/api/profile/update', headers=headers, json={'skills': [], 'domains': []}).json()
        self.assertEqual(cleared['skills'], [])
        self.assertEqual(cleared['domains'], [])
        self.assertLess(cleared['profile_completeness'], profile['profile_completeness'])

    def test_saved_alias_is_idempotent_and_isolated(self):
        headers = self.signup()
        for _ in range(2):
            self.assertEqual(self.client.post('/api/opportunities/reliance/save', headers=headers).status_code, 200)
        saved = self.client.get('/api/opportunities/saved', headers=headers).json()
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]['id'], 'reliance')
        self.assertEqual(self.client.get('/api/opportunities/saved').json(), [])
        self.assertTrue(self.client.get('/api/saved', headers=headers).json())
        self.assertEqual(self.client.delete('/api/opportunities/reliance/save', headers=headers).status_code, 200)
        self.assertEqual(self.client.get('/api/opportunities/saved', headers=headers).json(), [])
        self.assertEqual(self.client.get('/api/saved', headers=headers).json(), [])

    def test_application_status_keeps_documents_and_exports_calendar(self):
        doc = self.client.get('/api/opportunities/reliance/how-to-apply').json()['required_documents'][0]
        result = self.client.post('/api/applications/track', json={'opportunity_id': 'reliance', 'status': 'Draft', 'checked_documents': [doc]})
        self.assertEqual(result.status_code, 200, result.text)
        for status in ('Applied', 'Under Review', 'Interview'):
            updated = self.client.post('/api/applications/track', json={'opportunity_id': 'reliance', 'status': status})
            self.assertEqual(updated.status_code, 200)
            self.assertEqual(updated.json()['checked_documents'], [doc])
        overview = self.client.get('/api/applications/overview').json()
        self.assertEqual(overview['applications'][0]['application_status'], 'Interview')
        export = self.client.get('/api/applications/calendar.ics')
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export.text.count('BEGIN:VCALENDAR'), 1)
        self.assertEqual(export.text.count('BEGIN:VEVENT'), 1)
        self.assertIn('TRIGGER:-PT72H', export.text)
        self.assertEqual(self.client.delete('/api/applications/tracked/reliance').status_code, 200)
        self.assertEqual(self.client.get('/api/applications/overview').json()['applications'], [])
        self.assertEqual(self.client.get('/api/applications/calendar.ics').status_code, 409)

    def test_assistant_stream_preserves_markdown_and_metadata(self):
        query = {'query': 'How do I apply for Airtel and combine it with Delhi MCM?'}
        answer = self.client.post('/api/assistant/ask', json=query).json()
        stream = self.client.post('/api/assistant/ask', json={**query, 'stream': True})
        self.assertEqual(stream.status_code, 200)
        self.assertIn('text/event-stream', stream.headers['content-type'])
        deltas, final = [], None
        for event in stream.text.replace('\r\n', '\n').split('\n\n'):
            lines = event.splitlines()
            if len(lines) < 2:
                continue
            payload = json.loads(lines[1].removeprefix('data: '))
            if lines[0] == 'event: delta': deltas.append(payload['text'])
            if lines[0] == 'event: complete': final = payload
        self.assertEqual(''.join(deltas), answer['answer'])
        self.assertEqual(final['matched_opportunities'], answer['matched_opportunities'])
        self.assertTrue(final['policy_conflicts'])

    def test_guest_workspaces_are_private_and_invalid_tokens_do_not_write_to_demo(self):
        first = self.client.get('/api/profile').json()
        self.assertEqual(first['workspace_kind'], 'guest')
        self.client.post('/api/profile/update', json={'name': 'Private guest name'})
        self.client.post('/api/opportunities/reliance/save')
        cookie = self.client.cookies.get('iris_workspace')
        self.client.cookies.clear()
        second = self.client.get('/api/profile').json()
        self.assertNotEqual(second['id'], first['id'])
        self.assertNotEqual(second['name'], 'Private guest name')
        self.assertEqual(self.client.get('/api/opportunities/saved').json(), [])
        rejected = self.client.post('/api/profile/update', headers={'Authorization': 'Bearer expired-or-invalid'}, json={'name': 'Must not save'})
        self.assertEqual(rejected.status_code, 401)
        self.assertNotEqual(self.client.get('/api/profile').json()['name'], 'Must not save')
        self.client.cookies.clear()
        self.client.cookies.set('iris_workspace', cookie)
        self.assertEqual(self.client.get('/api/profile').json()['name'], 'Private guest name')
        self.assertEqual(len(self.client.get('/api/opportunities/saved').json()), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
