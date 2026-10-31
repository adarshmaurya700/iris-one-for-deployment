"""Gemini contracts/failure tests. All network calls here are mocked, never billed."""
import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, patch
import httpx
from providers import gemini_generate, safe_provider_error
from runtime_config import gemini_model
from gemini_extractor import extract_student_profile, extract_verified_opportunity


def response(text='{"status":"ok"}', status=200, error=None):
    data = {'error': error or {'status': 'UNAVAILABLE'}} if status != 200 else {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': text}]}}]}
    return httpx.Response(status, json=data, request=httpx.Request('POST', 'https://generativelanguage.googleapis.com/v1beta/models/test:generateContent'))


class GeminiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'IRIS_MODE': 'live', 'GEMINI_API_KEY': 'unit-test-secret',
            'GEMINI_MODEL': 'gemini-3.1-flash-lite', 'GEMINI_MAX_RETRIES': '1'})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    async def test_environment_selects_actual_request_model(self):
        with patch('httpx.AsyncClient.post', new=AsyncMock(return_value=response())) as remote:
            self.assertEqual(await gemini_generate('rules', 'input', json_output=True), {'status': 'ok'})
        self.assertTrue(remote.call_args.args[0].endswith('/models/gemini-3.1-flash-lite:generateContent'))
        self.assertNotIn('unit-test-secret', remote.call_args.args[0])
        self.assertEqual(remote.call_args.kwargs['headers']['x-goog-api-key'], 'unit-test-secret')

    async def test_modern_model_omits_deprecated_sampling(self):
        with patch.dict(os.environ, {'GEMINI_MODEL': 'models/gemini-3.8-flash'}), patch('httpx.AsyncClient.post', new=AsyncMock(return_value=response())) as remote:
            await gemini_generate('rules', 'input', json_output=True)
        config = remote.call_args.kwargs['json']['generationConfig']
        self.assertNotIn('temperature', config)
        self.assertEqual(config['thinkingConfig'], {'thinkingLevel': 'low'})

    async def test_retired_model_is_not_retried_or_silently_changed(self):
        with patch.dict(os.environ, {'GEMINI_MODEL': 'gemini-2.5-flash'}), patch('httpx.AsyncClient.post', new=AsyncMock(return_value=response(status=404, error={'status': 'NOT_FOUND'}))) as remote:
            with self.assertRaises(httpx.HTTPStatusError):
                await gemini_generate('rules', 'input')
            self.assertEqual(remote.call_count, 1)
            self.assertEqual(gemini_model(), 'gemini-2.5-flash')

    async def test_transient_rejection_retries_same_model_once(self):
        with patch('httpx.AsyncClient.post', new=AsyncMock(side_effect=[response(status=503), response()])) as remote, patch('providers.asyncio.sleep', new=AsyncMock()):
            self.assertEqual(await gemini_generate('rules', 'input', json_output=True), {'status': 'ok'})
            self.assertEqual(remote.call_count, 2)
            self.assertEqual(remote.call_args_list[0].args, remote.call_args_list[1].args)

    async def test_retry_budget_is_bounded_and_timeout_is_not_retried(self):
        with patch('httpx.AsyncClient.post', new=AsyncMock(return_value=response(status=503))) as remote, patch('providers.asyncio.sleep', new=AsyncMock()):
            with self.assertRaises(httpx.HTTPStatusError): await gemini_generate('rules', 'input')
            self.assertEqual(remote.call_count, 2)
        with patch('httpx.AsyncClient.post', new=AsyncMock(side_effect=httpx.ReadTimeout('private'))) as remote:
            with self.assertRaises(httpx.ReadTimeout): await gemini_generate('rules', 'input')
            self.assertEqual(remote.call_count, 1)

    async def test_error_diagnostics_exclude_upstream_messages_and_key(self):
        result = response(status=403, error={'status': 'PERMISSION_DENIED', 'message': 'unit-test-secret private resume', 'details': [{'reason': 'API_KEY_INVALID'}]})
        try: result.raise_for_status()
        except Exception as exc: data = safe_provider_error(exc)
        self.assertEqual(data['reason'], 'API_KEY_INVALID')
        self.assertNotIn('unit-test-secret', json.dumps(data))
        self.assertNotIn('private resume', json.dumps(data))
        with patch('httpx.AsyncClient.post', new=AsyncMock(return_value=result)), self.assertLogs('iris.integrations', level='WARNING') as logs:
            with self.assertRaises(httpx.HTTPStatusError):
                await gemini_generate('private resume', 'input')
        self.assertNotIn('unit-test-secret', ' '.join(logs.output))
        self.assertNotIn('private resume', ' '.join(logs.output))

    async def test_opportunity_schema_and_model_provenance(self):
        data = {'title': 'Example program', 'provider': 'Example', 'category': 'Student Offers', 'deadline_iso': None}
        with patch('httpx.AsyncClient.post', new=AsyncMock(return_value=response(json.dumps(data)))) as remote:
            result = await extract_verified_opportunity('Program facts', source_url='https://example.org')
        self.assertEqual(result['diagnostic_status'], 'LIVE_SUCCESS')
        self.assertEqual(result['provider_used'], 'google_gemini')
        self.assertEqual(result['model_used'], 'gemini-3.1-flash-lite')
        self.assertFalse(result['is_verified_active'])
        self.assertEqual(result['verification_status'], 'VERIFICATION_PENDING')
        self.assertIn('responseJsonSchema', remote.call_args.kwargs['json']['generationConfig'])

    async def test_invalid_extraction_never_claims_real_success(self):
        with patch('httpx.AsyncClient.post', new=AsyncMock(return_value=response('{"made_up":"data"}'))):
            result = await extract_verified_opportunity('Program facts', source_url='https://example.org')
        self.assertEqual(result['diagnostic_status'], 'LOCAL_FALLBACK')
        self.assertEqual(result['upstream_status'], 'LIVE_FAILED')
        self.assertFalse(result['is_verified_active'])

    async def test_resume_retains_explicit_income_and_does_not_invent_age(self):
        with patch('httpx.AsyncClient.post', new=AsyncMock(return_value=response('{"name":"Avery Example","family_income_lpa":4.8,"extracted_skills":["Python"]}'))):
            result = await extract_student_profile('Avery Example. Income 4.8 LPA. Python.')
        self.assertEqual(result['family_income_lpa'], 4.8)
        self.assertNotIn('age', result)
        self.assertEqual(result['model_used'], 'gemini-3.1-flash-lite')

    async def test_configuration_and_disabled_demo_never_contact_google(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'YOUR_ACTUAL_API_KEY'}), patch('httpx.AsyncClient.post', new_callable=AsyncMock) as remote:
            result = await extract_student_profile('Avery Example. Skills: Python')
            remote.assert_not_called()
            self.assertEqual(result['upstream_status'], 'NOT_CONFIGURED')
        with patch.dict(os.environ, {'IRIS_MODE': 'demo'}), patch('httpx.AsyncClient.post', new_callable=AsyncMock) as remote:
            result = await extract_student_profile('Avery Example. Skills: Python')
            remote.assert_not_called()
            self.assertEqual(result['diagnostic_status'], 'LOCAL_FALLBACK')

    async def test_model_setting_rejects_urls(self):
        with patch.dict(os.environ, {'GEMINI_MODEL': 'https://example.org/model'}):
            with self.assertRaises(ValueError): gemini_model()
