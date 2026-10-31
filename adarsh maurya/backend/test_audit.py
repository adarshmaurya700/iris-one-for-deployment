"""Regression cases for the hackathon audit. Disposable data and mocked providers only."""
import asyncio
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import AsyncMock, patch
import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request
import test_backend as fixtures
from main import app
from auth import SECRET_KEY, hash_password, verify_password
from catalog import verification_state
from matcher import calculate_match, evaluate_match_and_conflicts, eligibility_checklist
from database import find_opportunity, get_db
from application_service import DEMO_PROFILE
from runtime_config import validate_runtime
from security import public_url, SlidingWindowRateLimiter, assistant_limit
from verification import verify_catalog_record


class AuditTests(unittest.TestCase):
    setUp = fixtures.BackendTests.setUp
    tearDown = fixtures.BackendTests.tearDown
    db = fixtures.BackendTests.db
    signup = fixtures.BackendTests.signup

    def test_hash_itself_cannot_authenticate(self):
        headers = self.signup()
        hashed = self.db().execute('SELECT password_hash FROM users').fetchone()[0]
        self.assertFalse(verify_password(hashed, hashed))
        self.assertFalse(verify_password('plaintext', 'plaintext'))
        self.assertEqual(self.client.post('/api/auth/login', json={'email':'student@example.test','password':hashed}).status_code,401)
        self.assertTrue(verify_password('Password123!', hashed))

    def test_password_byte_limit_and_email_validation(self):
        for password in ('short', 'é'*40):
            result = self.client.post('/api/auth/signup', json={'email':'s@example.test','name':'Student','password':password})
            self.assertEqual(result.status_code,422)
        result=self.client.post('/api/auth/signup',json={'email':'invalid','name':'Student','password':'Password123!'})
        self.assertEqual(result.status_code,422)

    def test_token_requires_expiry_and_rejects_public_old_secret(self):
        self.signup()
        import jwt
        for token in (jwt.encode({'sub':'1'},SECRET_KEY,algorithm='HS256'),jwt.encode({'sub':'1','exp':9999999999,'iat':1},'iris_one_secret_key_2026',algorithm='HS256')):
            self.assertEqual(self.client.get('/api/auth/me',headers={'Authorization':'Bearer '+token}).status_code,401)

    def test_calendar_requires_its_owner_and_never_invents_dates(self):
        first=self.signup(); second=self.signup('other@example.test')
        self.client.post('/api/saved/reliance',headers=first)
        self.assertEqual(self.client.get('/api/users/1/calendar.ics').status_code,401)
        self.assertEqual(self.client.get('/api/users/1/calendar.ics',headers=second).status_code,403)
        result=self.client.get('/api/users/1/calendar.ics',headers=first)
        self.assertEqual(result.status_code,200); self.assertIn('VALARM',result.text)
        self.assertEqual(self.client.get('/api/opportunities/gemini-student/ics').status_code,409)

    def test_security_headers_and_cors(self):
        result=self.client.get('/api/profile',headers={'Origin':'https://attacker.example'})
        self.assertNotIn('access-control-allow-origin',result.headers)
        self.assertEqual(result.headers['cache-control'],'no-store')
        self.assertIn("script-src 'self'",result.headers['content-security-policy'])
        self.assertEqual(result.headers['x-content-type-options'],'nosniff')

    def test_production_rejects_missing_or_weak_secrets(self):
        with patch.dict(os.environ,{'IRIS_ENV':'production','JWT_SECRET':'','IRIS_ADMIN_KEY':''}):
            with self.assertRaises(RuntimeError): validate_runtime()
        with patch.dict(os.environ,{'IRIS_ENV':'production','JWT_SECRET':'x'*40,'IRIS_ADMIN_KEY':'y'*40,'ALLOWED_ORIGINS':'*'}):
            with self.assertRaises(RuntimeError): validate_runtime()
        with patch.dict(os.environ,{'IRIS_ENV':'production','JWT_SECRET':'x'*40,'IRIS_ADMIN_KEY':'y'*40,'ALLOWED_ORIGINS':''}):
            validate_runtime()

    def test_admin_and_production_verification_are_protected(self):
        with patch.dict(os.environ,{'IRIS_ADMIN_KEY':'test-admin-secret','IRIS_ENV':'production'}):
            self.assertEqual(self.client.get('/api/admin/diagnostics').status_code,403)
            self.assertEqual(self.client.post('/api/admin/refresh-catalog').status_code,403)
            self.assertEqual(self.client.get('/api/verify-opportunity/airtel').status_code,401)
            self.assertEqual(self.client.post('/api/sync/trigger',json={'live':True}).status_code,401)
            result=self.client.get('/api/admin/diagnostics',headers={'X-IRIS-Admin-Key':'test-admin-secret'})
            self.assertEqual(result.status_code,200)
            self.assertNotIn('test-admin-secret',result.text)

    def test_forwarded_header_does_not_bypass_limits(self):
        limiter=SlidingWindowRateLimiter(1,60)
        def request(ip):
            return Request({'type':'http','client':('127.0.0.1',123),'headers':[(b'x-forwarded-for',ip.encode())]})
        limiter.check(request('1.1.1.1'))
        with self.assertRaises(HTTPException) as failure: limiter.check(request('2.2.2.2'))
        self.assertEqual(failure.exception.status_code,429)
        with patch.object(assistant_limit,'max_requests',0):
            self.assertEqual(self.client.post('/api/assistant/ask',json={'query':'Hello'}).status_code,429)

    def test_public_url_guard_rejects_local_sources(self):
        for url in ('http://127.0.0.1','http://10.0.0.1','http://169.254.169.254','http://localhost','http://[::1]','https://user:password@example.org','file:///etc/passwd','https://example.org:8000'):
            with self.subTest(url=url), self.assertRaises(ValueError): public_url(url,resolve=False)
        self.assertEqual(public_url('https://example.org/apply',resolve=False),'https://example.org/apply')

    def test_blank_guest_is_not_the_sample_student(self):
        result=self.client.get('/api/profile').json()
        self.assertEqual(result['name'],'')
        self.assertIsNone(result['family_income_inr']); self.assertIsNone(result['class_12_pct'])
        self.assertEqual(result['skills'],[])
        self.assertEqual(result['profile_completeness'],0)

    def test_demo_mode_is_explicit_and_never_calls_models(self):
        with patch.dict(os.environ,{'IRIS_MODE':'demo','GEMINI_API_KEY':'test','TINYFISH_API_KEY':'test','GROQ_API_KEY':'test'}), patch('httpx.AsyncClient.post',new_callable=AsyncMock) as remote:
            result=self.client.post('/api/assistant/ask',json={'query':'Airtel documents'}).json()
            verification=self.client.post('/api/verify-opportunity',json={'opportunity_id':'airtel'}).json()
            remote.assert_not_called()
            self.assertTrue(result['is_simulated']); self.assertTrue(verification['is_simulated'])
            self.assertFalse(verification['is_verified'])

    def test_empty_live_database_does_not_silently_seed_fixtures(self):
        path=str(Path(self.tmp.name)/'empty-live.db')
        with patch.dict(os.environ,{'DATABASE_PATH':path,'IRIS_MODE':'live','IRIS_SEED_REFERENCE':''}):
            with TestClient(app) as client:
                self.assertEqual(client.get('/api/opportunities').json(),[])

    def test_unknown_eligibility_is_never_passed(self):
        opp={**find_opportunity(self.db(),'airtel'),'deadline_iso':'2099-12-31'}
        profile={**DEMO_PROFILE,'class_12_pct':None,'family_income_inr':None,'nirf_top_50':None}
        match=evaluate_match_and_conflicts(profile,opp,[])
        self.assertFalse(match['eligible']); self.assertEqual(match['eligibility_status'],'requires_information')
        unknown=[item for item in eligibility_checklist(profile,opp) if item['status']=='unknown']
        self.assertEqual(len(unknown),3); self.assertTrue(all(item['pass'] is None for item in unknown))

    def test_compatibility_weights_and_expiry(self):
        opp=find_opportunity(self.db(),'airtel')
        result=evaluate_match_and_conflicts({**DEMO_PROFILE,'nirf_top_50':1},opp,[])
        self.assertEqual(result['eligibility_status'],'not_eligible')
        empty=calculate_match({},opp)
        self.assertLess(empty['overall'],65)
        self.assertEqual(sum(item['points'] for item in empty['breakdown']),empty['overall'])
        self.assertEqual([item['weight'] for item in empty['breakdown']],['35 pts','25 pts','25 pts','15 pts'])

    def test_all_views_share_the_same_score(self):
        db=self.db(); db.execute("UPDATE opportunities SET deadline_iso='2099-12-31', deadline='2099-12-31' WHERE slug='airtel'"); db.commit()
        self.client.post('/api/profile/update',json={'name':'Alice','academic_stage':'B.Tech','state_domicile':'Delhi','skills':['Python'],'class_12_pct':90,'family_income_inr':300000,'nirf_top_50':True})
        feed=next(item for item in self.client.get('/api/opportunities').json() if item['id']=='airtel')
        detail=self.client.get('/api/opportunities/airtel').json()
        guide=self.client.get('/api/opportunities/airtel/how-to-apply').json()
        answer=self.client.post('/api/assistant/ask',json={'query':'Why this match?','opportunity_id':'airtel'}).json()
        card=next(item for item in answer['matched_opportunities'] if item['id']=='airtel')
        self.assertEqual(feed['match_score'],detail['match_score']); self.assertEqual(guide['match_score'],card['match_score']); self.assertEqual(feed['match_score'],guide['match_score'])
        self.assertIn('academic',answer['answer']); self.assertIn('not selection odds',answer['answer'])

    def test_live_badge_expires_without_scheduler(self):
        db=self.db(); stamp=(datetime.now(timezone.utc)-timedelta(hours=13)).isoformat()
        db.execute("UPDATE opportunities SET verification_status='VERIFIED_LIVE',last_verified_at=?, deadline_iso='2099-12-31', application_channels_json=? WHERE slug='airtel'",(stamp,json.dumps([{'url':'https://example.org','verified':True,'badge':'Apply Live'}]))); db.commit()
        self.client.post('/api/opportunities/airtel/save')
        for url in ('/api/opportunities/airtel','/api/opportunities/saved','/api/opportunities/airtel/how-to-apply'):
            data=self.client.get(url).json(); data=data[0] if isinstance(data,list) else data
            self.assertEqual(data['verification_status'],'PREVIOUSLY_VERIFIED')
        guide=self.client.get('/api/opportunities/airtel/how-to-apply').json()
        self.assertFalse(guide['application_channels'][0]['verified'])

    def test_fresh_badge_requires_a_real_timestamp(self):
        base={'verification_status':'VERIFIED_LIVE','application_channels_json':'[]'}
        self.assertFalse(verification_state(base)['is_live_verified'])
        self.assertTrue(verification_state({**base,'last_verified_at':datetime.now(timezone.utc).isoformat()})['is_live_verified'])
        self.assertFalse(verification_state({**base,'last_verified_at':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()})['is_live_verified'])

    def test_arbitrary_resume_never_invents_student_facts(self):
        result=self.client.post('/api/resume/analyze',files={'file':('alice.txt',b'Alice Example\nSkills: SQL','text/plain')})
        self.assertEqual(result.status_code,200,result.text)
        profile=self.client.get('/api/profile').json()
        self.assertEqual(profile['name'],'Alice Example'); self.assertIsNone(profile['age']); self.assertIsNone(profile['family_income_inr']); self.assertIsNone(profile['class_12_pct'])
        self.assertEqual(profile['skills'],['SQL']); self.assertNotIn('resume_text',result.json()['student_profile'])

    def test_resume_rejects_empty_corrupt_and_oversized_content(self):
        self.assertEqual(self.client.post('/api/resume/analyze',json={}).status_code,400)
        self.assertEqual(self.client.post('/api/resume/analyze',files={'file':('bad.pdf',b'not a PDF','application/pdf')}).status_code,400)
        self.assertEqual(self.client.post('/api/resume/analyze',json={'text':'a'*100001}).status_code,413)
        self.assertEqual(self.client.post('/api/resume/analyze',json={'use_sample':True}).status_code,409)

    def test_compressed_document_expansion_is_bounded(self):
        from zipfile import ZipFile,ZIP_DEFLATED
        data=io.BytesIO()
        with ZipFile(data,'w',ZIP_DEFLATED) as archive: archive.writestr('word/document.xml',b'x'*(21*1024*1024))
        self.assertEqual(self.client.post('/api/resume/analyze',files={'file':('bomb.docx',data.getvalue())}).status_code,400)

    def test_oversized_request_is_rejected_before_parsing(self):
        self.assertEqual(self.client.post('/api/profile/update',content=b'x'*(256*1024+1),headers={'content-type':'application/json'}).status_code,413)

    def test_resume_removal_and_export_are_scoped(self):
        first=self.signup();second=self.signup('other@example.test')
        self.client.post('/api/resume/analyze',headers=first,files={'file':('alice.txt',b'Alice Example\nSkills: Python','text/plain')})
        exported=self.client.get('/api/profile/export',headers=first)
        self.assertEqual(exported.status_code,200);self.assertIn('attachment',exported.headers['content-disposition'])
        self.assertEqual(self.client.get('/api/profile/export',headers=second).json()['profile']['resume_filename'],'')
        self.client.delete('/api/profile/resume',headers=second)
        self.assertTrue(self.client.get('/api/profile',headers=first).json()['resume_filename'])
        self.client.delete('/api/profile/resume',headers=first)
        row=self.db().execute("SELECT resume_text FROM student_profiles WHERE id='user:1'").fetchone()
        self.assertEqual(row[0],'')

    def test_clear_eligibility_fields_and_restart_persistence(self):
        headers=self.signup()
        self.client.post('/api/profile/update',headers=headers,json={'class_12_pct':90,'family_income_inr':300000,'nirf_top_50':True})
        self.client.post('/api/profile/update',headers=headers,json={'class_12_pct':None,'family_income_inr':None,'nirf_top_50':None})
        self.client.post('/api/opportunities/reliance/save',headers=headers)
        self.client.post('/api/applications/track',headers=headers,json={'opportunity_id':'reliance','status':'Interview'})
        with TestClient(app) as restarted:
            profile=restarted.get('/api/profile',headers=headers).json()
            self.assertIsNone(profile['class_12_pct']);self.assertIsNone(profile['family_income_inr'])
            self.assertEqual(len(restarted.get('/api/opportunities/saved',headers=headers).json()),1)
            self.assertEqual(restarted.get('/api/applications/overview',headers=headers).json()['applications'][0]['application_status'],'Interview')

    def test_gemini_fenced_json_and_header_authentication(self):
        from providers import gemini_generate
        response=httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':'```json\n{"status":"ok"}\n```'}]}}]},request=httpx.Request('POST','https://example.org'))
        with patch.dict(os.environ,{'GEMINI_API_KEY':'audit-secret'}),patch('httpx.AsyncClient.post',new=AsyncMock(return_value=response)) as remote:
            self.assertEqual(asyncio.run(gemini_generate('Rules','Data',json_output=True)),{'status':'ok'})
            self.assertNotIn('audit-secret',remote.call_args.args[0]);self.assertEqual(remote.call_args.kwargs['headers']['x-goog-api-key'],'audit-secret')

    def test_provider_cascade_and_untrusted_data_boundary(self):
        response=httpx.Response(200,json={'choices':[{'message':{'content':'Grounded answer from local records.'}}]},request=httpx.Request('POST','https://example.org'))
        failure=httpx.ReadTimeout('sensitive-url-must-not-be-logged')
        with patch.dict(os.environ,{'GEMINI_API_KEY':'test','GROQ_API_KEY':'test'}),patch('httpx.AsyncClient.post',new=AsyncMock(side_effect=[failure,response])) as remote:
            result=self.client.post('/api/assistant/ask',json={'query':'Airtel documents'}).json()
            self.assertEqual(result['model_used'],'llama-3.3-70b-versatile')
            messages=remote.call_args.kwargs['json']['messages']
            self.assertNotIn('Bharti',messages[0]['content']);self.assertIn('Bharti',messages[1]['content'])
            self.assertNotIn('resume_text',messages[1]['content'])

    def test_invalid_model_json_uses_identified_fallback(self):
        response=httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':'{invalid'}]}}]},request=httpx.Request('POST','https://example.org'))
        with patch.dict(os.environ,{'GEMINI_API_KEY':'test'}),patch('httpx.AsyncClient.post',new=AsyncMock(return_value=response)):
            result=self.client.post('/api/resume/analyze',files={'file':('a.txt',b'Alice Example\nSkills: Python','text/plain')}).json()
            self.assertEqual(result['profile']['diagnostic_status'],'LOCAL_FALLBACK')
            self.assertEqual(result['profile']['name'],'Alice Example')

    def test_missing_gemini_does_not_start_billed_verification(self):
        with patch('tinyfish_pipeline._get_api_key',return_value='test'),patch('tinyfish_pipeline._call_tinyfish_search',new_callable=AsyncMock) as search:
            result=asyncio.run(verify_catalog_record({'title':'Example'}))
            search.assert_not_called();self.assertEqual(result['diagnostic_status'],'NOT_CONFIGURED')

    def test_tinyfetch_errors_and_agent_failure_never_succeed(self):
        from tinyfish_pipeline import tinyfetch,tinyagent
        bad_fetch=httpx.Response(200,json={'results':[],'errors':[{'message':'blocked'}]},request=httpx.Request('POST','https://example.org'))
        with patch('tinyfish_pipeline.public_url',side_effect=lambda u:u),patch.dict(os.environ,{'TINYFISH_API_KEY':'test'}),patch('httpx.AsyncClient.post',new=AsyncMock(return_value=bad_fetch)):
            with self.assertRaises(ValueError): asyncio.run(tinyfetch('https://example.org'))
        failed=httpx.Response(200,json={'status':'FAILED','result':{'is_button_live':True}},request=httpx.Request('POST','https://example.org'))
        with patch('tinyfish_pipeline.public_url',side_effect=lambda u:u),patch.dict(os.environ,{'TINYFISH_API_KEY':'test'}),patch('httpx.AsyncClient.post',new=AsyncMock(return_value=failed)) as remote:
            with self.assertRaises(ValueError): asyncio.run(tinyagent('https://example.org'))
            self.assertEqual(remote.call_count,1)

    def test_failed_postgres_never_switches_in_production(self):
        import database
        with patch.dict(os.environ,{'IRIS_ENV':'production','DATABASE_URL':'postgresql://invalid:invalid@127.0.0.1:1/test'}):
            database._postgres_available=None
            with self.assertRaises(Exception): get_db()
        database._postgres_available=None

    def test_telegram_does_not_claim_preview_delivery_or_allow_other_chats(self):
        self.assertEqual(self.client.post('/api/notifications/telegram-test',json={}).status_code,401)
        headers=self.signup()
        self.assertEqual(self.client.post('/api/notifications/telegram-test',headers=headers,json={'chat_id':'someone-else'}).status_code,403)
        result=self.client.post('/api/notifications/telegram-test',headers=headers,json={'preview':True}).json()
        self.assertFalse(result['delivered']);self.assertFalse(result['success'])

    def test_partial_extraction_retains_known_rules_and_expired_date(self):
        payload={'title':'Example','provider':'Example','apply_url':'https://example.org/apply','how_to_apply_steps':[{'step':1,'title':'Register','detail':'Read official terms.'}],'required_documents':['Student ID']}
        opp={'title':'Example','apply_url':'https://example.org/apply','deadline_iso':'2020-01-01','min_marks_pct':90,'max_family_income_inr':400000}
        with patch.dict(os.environ,{'GEMINI_API_KEY':'test'}),patch('tinyfish_pipeline._get_api_key',return_value='test'),patch('verification.public_url',side_effect=lambda url:url),patch('tinyfish_pipeline._call_tinyfish_search',new=AsyncMock(return_value={'results':[]})),patch('tinyfish_pipeline._call_tinyfish_fetch',new=AsyncMock(return_value={'markdown':'Recorded program details'})),patch('tinyfish_pipeline._call_tinyfish_agent',new=AsyncMock(return_value={'result':{'is_button_live':True,'application_url':'https://example.org/apply','evidence':'An apply link is displayed'}})),patch('verification.gemini_generate',new=AsyncMock(return_value=payload)):
            result=asyncio.run(verify_catalog_record(opp))
        self.assertEqual(result['verification_status'],'EXPIRED')
        self.assertNotIn('min_marks_pct',result['fields']);self.assertNotIn('deadline_iso',result['fields']);self.assertNotIn('max_family_income_inr',result['fields'])

    def test_application_domain_must_match_inspected_action(self):
        payload={'title':'Example','provider':'Example','apply_url':'https://different.example/apply','how_to_apply_steps':[{'step':1,'title':'Register','detail':'Read official terms.'}],'required_documents':['Student ID']}
        with patch.dict(os.environ,{'GEMINI_API_KEY':'test'}),patch('tinyfish_pipeline._get_api_key',return_value='test'),patch('verification.public_url',side_effect=lambda url:url),patch('tinyfish_pipeline._call_tinyfish_search',new=AsyncMock(return_value={'results':[]})),patch('tinyfish_pipeline._call_tinyfish_fetch',new=AsyncMock(return_value={'markdown':'Recorded program details'})),patch('tinyfish_pipeline._call_tinyfish_agent',new=AsyncMock(return_value={'result':{'is_button_live':True,'application_url':'https://example.org/apply','evidence':'An apply link is displayed'}})),patch('verification.gemini_generate',new=AsyncMock(return_value=payload)):
            result=asyncio.run(verify_catalog_record({'title':'Example','apply_url':'https://example.org'}))
        self.assertEqual(result['verification_status'],'COULD_NOT_VERIFY');self.assertFalse(result['last_verified_at'])

    def test_legacy_and_new_saved_apis_stay_synchronized(self):
        headers=self.signup()
        self.client.post('/api/opportunities/reliance/save',headers=headers)
        self.client.delete('/api/saved/reliance',headers=headers)
        self.assertEqual(self.client.get('/api/opportunities/saved',headers=headers).json(),[])
        self.client.post('/api/applications/reliance',headers=headers)
        self.assertEqual(self.client.get('/api/opportunities/reliance/how-to-apply',headers=headers).json()['tracking_status'],'Applied')

    def test_guest_feed_flags_and_counts_use_its_workspace(self):
        self.client.post('/api/opportunities/reliance/save')
        self.client.post('/api/applications/track',json={'opportunity_id':'reliance','status':'Draft'})
        detail=self.client.get('/api/opportunities/reliance').json()
        self.assertTrue(detail['is_saved']);self.assertTrue(detail['is_applied'])
        stats=self.client.get('/api/dashboard/stats').json()
        self.assertEqual(stats['saved_count'],1);self.assertEqual(stats['applied_count'],1)

    def test_unknown_program_conditions_need_more_information(self):
        opp={'title':'Unknown rules','academic_tier':'ALL','location_state':'All India','how_to_apply_steps_json':'[{"step":1}]'}
        result=evaluate_match_and_conflicts(DEMO_PROFILE,opp,[])
        self.assertFalse(result['eligible']);self.assertEqual(result['eligibility_status'],'requires_information')


if __name__ == '__main__': unittest.main()
