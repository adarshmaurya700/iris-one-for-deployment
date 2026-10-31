"""One Gemini REST contract for extraction, chat and bounded diagnostics."""
import json
import re
import asyncio
import os
import httpx
from diagnostics import record
from runtime_config import credential, mode, gemini_model


def safe_provider_error(error):
    """Retain machine-readable failure causes, never response messages/prompts/keys."""
    response = getattr(error, 'response', None)
    data = {}
    if response is not None:
        try:
            data = response.json().get('error') or {}
        except (ValueError, AttributeError):
            pass
    if not isinstance(data, dict):
        data = {}
    def code(value):
        return value if isinstance(value, str) and re.fullmatch(r'[A-Z_]{1,80}', value) else None
    reasons = [code(item.get('reason')) for item in (data.get('details') or []) if isinstance(item, dict)]
    return {'error_type': type(error).__name__, 'http_status': getattr(response, 'status_code', None),
            'api_status': code(data.get('status')), 'reason': next((item for item in reasons if item), None)}


def parse_json(text):
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip(), flags=re.I)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError('Expected a JSON object.')
    return data


async def gemini_generate(instruction, text='', *, json_output=False, contents=None, max_tokens=3000, response_schema=None):
    key = credential('GEMINI_API_KEY')
    model = gemini_model()
    if not key or mode() == 'demo':
        record('Gemini', 'NOT_CONFIGURED' if not key else 'LOCAL_FALLBACK', model=model)
        raise RuntimeError('Live Gemini is unavailable; configure GEMINI_API_KEY and IRIS_MODE=live.')
    generation = {'maxOutputTokens': max_tokens}
    # Gemini 3.6+ deprecates sampling parameters; leave their defaults intact.
    version = re.match(r'gemini-(\d+)(?:\.(\d+))?', model)
    modern = bool(version and (int(version[1]), int(version[2] or 0)) >= (3, 6))
    if not modern:
        generation['temperature'] = 0.1
    if model.startswith('gemini-3.8'):
        generation['thinkingConfig'] = {'thinkingLevel': 'low'}
    if model.startswith('gemini-2.5') and 'pro' not in model:
        generation['thinkingConfig'] = {'thinkingBudget': 0}
    if json_output:
        generation['responseMimeType'] = 'application/json'
        if response_schema:
            generation['responseJsonSchema'] = response_schema
    attempt = -1
    try:
        retries = int(os.environ.get('GEMINI_MAX_RETRIES', '1'))
        if retries not in (0, 1):
            raise ValueError('GEMINI_MAX_RETRIES must be 0 or 1.')
        # Retry only an explicit transient rejection, never an ambiguous timeout,
        # authentication failure or retired model. Keep the same selected model.
        async with asyncio.timeout(45), httpx.AsyncClient(timeout=httpx.Timeout(35, connect=8)) as client:
            for attempt in range(retries + 1):
                response = await client.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
                    headers={'x-goog-api-key': key}, json={
                        'systemInstruction': {'parts': [{'text': instruction}]},
                        'contents': contents or [{'role': 'user', 'parts': [{'text': text}]}],
                        'generationConfig': generation})
                if response.status_code not in (429, 503) or attempt == retries:
                    break
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    record('Gemini', 'LIVE_FAILED', model=model, error=exc, attempts=attempt + 1)
                await asyncio.sleep(2)
        response.raise_for_status()
        candidate = response.json()['candidates'][0]
        if candidate.get('finishReason', 'STOP') != 'STOP':
            raise ValueError('Model output was blocked or incomplete.')
        answer = ''.join(p.get('text', '') for p in candidate['content']['parts'] if not p.get('thought')).strip()
        if not answer:
            raise ValueError('Model returned no usable text.')
        result = parse_json(answer) if json_output else answer
        record('Gemini', 'LIVE_SUCCESS', model=model, attempts=attempt + 1)
        return result
    except Exception as exc:
        record('Gemini', 'LIVE_FAILED', model=model, error=exc, attempts=attempt + 1)
        raise
