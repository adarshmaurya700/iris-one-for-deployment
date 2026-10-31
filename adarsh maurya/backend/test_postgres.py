"""Integration test against a disposable pgvector DB (IRIS_TEST_POSTGRES_URL)."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import database


@unittest.skipUnless(os.environ.get('IRIS_TEST_POSTGRES_URL'), 'Disposable PostgreSQL URL not configured')
class PostgresTests(unittest.TestCase):
    def test_postgres_schema_vector_and_http_contracts(self):
        from fastapi.testclient import TestClient
        from main import app
        from seed_data import seed_opportunities
        with patch.dict(os.environ, {'DATABASE_URL': os.environ['IRIS_TEST_POSTGRES_URL'], 'IRIS_DISABLE_SCHEDULER': '1', 'IRIS_MODE': 'live', 'IRIS_SEED_REFERENCE': '1', 'TINYFISH_API_KEY': '', 'GEMINI_API_KEY': '', 'GROQ_API_KEY': '', 'OLLAMA_BASE_URL': ''}):
            database._postgres_available = None
            with TestClient(app) as client:
                db = database.get_db()
                try:
                    self.assertIsInstance(db, database.PostgresConnection)
                    self.assertGreater(db.execute('SELECT COUNT(*) FROM opportunities WHERE embedding IS NOT NULL').fetchone()[0], 20)
                    count = db.execute('SELECT COUNT(*) FROM opportunities').fetchone()[0]
                    seed_opportunities(db)
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM opportunities').fetchone()[0], count)
                finally:
                    db.close()
                response = client.post('/api/auth/signup', json={'email': 'postgres-test@example.test', 'name': 'PG Test', 'password': 'Password123!', 'college': 'B.Tech', 'state': 'Delhi'})
                if response.status_code != 201:
                    response = client.post('/api/auth/login', json={'email': 'postgres-test@example.test', 'password': 'Password123!'})
                self.assertIn(response.status_code, (200, 201), response.text)
                headers = {'Authorization': 'Bearer ' + response.json()['token']}
                self.assertEqual(client.post('/api/saved/reliance', headers=headers).status_code, 200)
                self.assertEqual(client.post('/api/applications/track', headers=headers, json={'opportunity_id': 'airtel'}).status_code, 200)
                self.assertEqual(client.get('/api/opportunities/airtel/how-to-apply', headers=headers).json()['tracking_status'], 'In Progress')
                self.assertEqual(client.post('/api/assistant/ask', headers=headers, json={'query': 'Airtel documents'}).status_code, 200)
                profile = client.post('/api/profile/update', headers=headers, json={'academic_stage': 'B.Tech (1st Year)', 'institution': 'GGSIPU USAR', 'graduation_year': 2028, 'skills': ['Python'], 'domains': ['Scholarships'], 'onboarding_complete': True, 'preferences': {'reduce_motion': True}})
                self.assertEqual(profile.status_code, 200, profile.text)
                self.assertEqual(client.get('/api/profile', headers=headers).json()['graduation_year'], 2028)
                self.assertEqual(client.post('/api/opportunities/reliance/save', headers=headers).status_code, 200)
                self.assertTrue(client.get('/api/opportunities/saved', headers=headers).json())
                self.assertEqual(client.post('/api/applications/track', headers=headers, json={'opportunity_id': 'reliance', 'status': 'Under Review'}).status_code, 200)
                self.assertTrue(client.get('/api/applications/overview', headers=headers).json()['applications'])
                self.assertEqual(client.get('/api/applications/calendar.ics', headers=headers).status_code, 200)
                stream = client.post('/api/assistant/ask', headers=headers, json={'query': 'Airtel documents', 'stream': True})
                self.assertEqual(stream.status_code, 200)
                self.assertIn('event: complete', stream.text)
                self.assertEqual(client.post('/api/sync/trigger', json={'live': False}).status_code, 202)
                self.assertEqual(client.get('/api/sync/status').json()['last_result']['status'], 'completed')
            database._postgres_available = None


if __name__ == '__main__':
    unittest.main(verbosity=2)
