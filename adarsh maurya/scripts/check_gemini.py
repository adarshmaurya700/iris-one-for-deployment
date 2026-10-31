"""Explicit real Gemini tests; disposable database, public/test inputs, redacted evidence.

Run: python -B scripts/check_gemini.py --live --model MODEL --output REPORT.json
No automatic model switching or repeated generation requests.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import env_loader  # noqa: E402, F401
from catalog import utc_now
from runtime_config import credential, gemini_model
from providers import gemini_generate, safe_provider_error

SOURCE_URL = 'https://docs.github.com/en/education/about-github-education/github-education-for-students/apply-to-github-education-as-a-student'
# Paraphrased from the official page, checked 31 October 2026. No deadline invented.
OPPORTUNITY_TEXT = '''GitHub Education provides developer resources for eligible students.
Applicants need to be enrolled in education leading to a degree or diploma, have
their own GitHub account, and be at least 13. They must prove current enrollment.
Possible evidence includes an enrollment letter, transcript, class schedule or a
current school ID. Some institutions require a verified academic email. Applications
are started in Education benefits settings. The page gives no application deadline,
income threshold, minimum marks or cash-award amount.'''

RESUME_TEXT = '''Avery Example
B.Tech Computer Science, Example University
Age: 20
Domicile: Delhi, India
Class 12 marks: 91%
Annual family income: INR 480000 (4.8 lakh per annum)
Skills: Python, FastAPI, SQL
Project: Built a student opportunity search application.
This is a synthetic integration-test resume, not a real student's document.'''


async def run(model=None):
    if model:
        os.environ['GEMINI_MODEL'] = model
    os.environ.update(IRIS_MODE='live', IRIS_DISABLE_SCHEDULER='1', IRIS_SEED_REFERENCE='1', DATABASE_URL='', GROQ_API_KEY='', OLLAMA_BASE_URL='')
    selected = gemini_model()
    report = {'checked_at': utc_now(), 'model': selected, 'key_configured': bool(credential('GEMINI_API_KEY')),
              'automatic_model_switching': False, 'tests': {},
              'input_provenance': {'opportunity': SOURCE_URL, 'resume': 'Synthetic test resume; no real private student data.'}}
    if not report['key_configured']:
        report['tests']['configuration'] = {'status': 'NOT_CONFIGURED'}
        return report

    import httpx
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.get(f'https://generativelanguage.googleapis.com/v1beta/models/{selected}', headers={'x-goog-api-key': credential('GEMINI_API_KEY')})
            response.raise_for_status()
            data = response.json()
            report['tests']['model_metadata'] = {'status': 'LIVE_SUCCESS', 'http_status': response.status_code,
                                                  'generation_methods': data.get('supportedGenerationMethods', [])}
    except Exception as exc:
        report['tests']['model_metadata'] = {'status': 'LIVE_FAILED', **safe_provider_error(exc)}

    try:
        data = await gemini_generate('Return JSON with status exactly ok.', 'Connectivity check.', json_output=True, max_tokens=512)
        if data != {'status': 'ok'}:
            raise ValueError('Unexpected probe output')
        report['tests']['generation'] = {'status': 'LIVE_SUCCESS', 'model_used': selected}
    except Exception as exc:
        report['tests']['generation'] = {'status': 'LIVE_FAILED', **safe_provider_error(exc)}

    from gemini_extractor import extract_verified_opportunity
    opportunity = await extract_verified_opportunity(OPPORTUNITY_TEXT, source_url=SOURCE_URL, query='GitHub Education student benefits')
    report['tests']['opportunity_extraction'] = {
        'status': opportunity['diagnostic_status'], 'provider_used': opportunity['provider_used'],
        'model_used': opportunity['model_used'], 'upstream_error': opportunity.get('upstream_error'),
        'schema_validated': opportunity['diagnostic_status'] == 'LIVE_SUCCESS',
        'title': opportunity['title'], 'deadline_iso': opportunity.get('deadline_iso'),
        'is_verified_active': opportunity['is_verified_active'],
        'note': 'Real model extraction; no TinyFish/application verification was performed.'}

    # Test the actual FastAPI resume and assistant contracts on an isolated DB.
    with tempfile.TemporaryDirectory(prefix='iris-gemini-probe-') as directory:
        os.environ['DATABASE_PATH'] = str(Path(directory) / 'probe.db')
        import database
        database._postgres_available = None
        from main import app
        from fastapi.testclient import TestClient
        with TestClient(app) as client:
            response = client.post('/api/resume/analyze', files={'file': ('test-resume.txt', RESUME_TEXT.encode(), 'text/plain')})
            data = response.json()
            profile = data.get('profile', {})
            stored = client.get('/api/profile').json()
            report['tests']['resume_upload_and_analysis'] = {
                'http_status': response.status_code, 'status': profile.get('diagnostic_status', 'LIVE_FAILED'),
                'provider_used': profile.get('provider_used'), 'model_used': profile.get('model_used'),
                'upstream_error': profile.get('upstream_error'),
                'name_matches_input': profile.get('name') == 'Avery Example',
                'skills_from_input': profile.get('extracted_skills', []),
                'persistence_checked': stored.get('resume_filename') == 'test-resume.txt' and stored.get('name') == 'Avery Example'}
            response = client.post('/api/assistant/ask', json={'query': 'What documents does the stored Airtel guide list? Mention if the record is expired.', 'opportunity_id': 'airtel'})
            answer = response.json()
            report['tests']['ask_iris'] = {
                'http_status': response.status_code, 'status': answer.get('diagnostic_status', 'LIVE_FAILED'),
                'model_used': answer.get('model_used'), 'answer_present': bool(answer.get('answer')),
                'source_cards': len(answer.get('matched_opportunities', [])),
                'note': 'Stored reference catalog was used only in the disposable test database.'}
    from diagnostics import snapshot
    report['diagnostics'] = snapshot()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Allow controlled real Gemini requests.')
    parser.add_argument('--model', help='Explicit model for this test process only.')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not args.live:
        parser.error('--live is required; no request was made.')
    report = asyncio.run(run(args.model))
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(output, encoding='utf-8')
    print(output)
