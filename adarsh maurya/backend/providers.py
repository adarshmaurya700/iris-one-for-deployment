"""One Gemini REST contract for extraction, chat and bounded diagnostics."""
import json
import re
import httpx
from diagnostics import record
from runtime_config import credential, mode


def parse_json(text):
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip(), flags=re.I)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError('Expected a JSON object.')
    return data


async def gemini_generate(instruction, text='', *, json_output=False, contents=None, max_tokens=3000):
    key = credential('GEMINI_API_KEY')
    model = __import__('os').environ.get('GEMINI_MODEL', 'gemini-2.5-flash')
    if not key or mode() == 'demo':
        record('Gemini', 'NOT_CONFIGURED' if not key else 'LOCAL_FALLBACK', model=model)
        raise RuntimeError('Live Gemini is unavailable; configure GEMINI_API_KEY and IRIS_MODE=live.')
    generation = {'temperature': 0.1, 'maxOutputTokens': max_tokens}
    if model.startswith('gemini-2.5') and 'pro' not in model:
        generation['thinkingConfig'] = {'thinkingBudget': 0}
    if json_output:
        generation['responseMimeType'] = 'application/json'
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(35, connect=8)) as client:
            response = await client.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
                headers={'x-goog-api-key': key}, json={
                    'systemInstruction': {'parts': [{'text': instruction}]},
                    'contents': contents or [{'role': 'user', 'parts': [{'text': text}]}],
                    'generationConfig': generation})
        response.raise_for_status()
        candidate = response.json()['candidates'][0]
        if candidate.get('finishReason', 'STOP') != 'STOP':
            raise ValueError('Model output was blocked or incomplete.')
        answer = ''.join(p.get('text', '') for p in candidate['content']['parts'] if not p.get('thought')).strip()
        if not answer:
            raise ValueError('Model returned no usable text.')
        result = parse_json(answer) if json_output else answer
        record('Gemini', 'LIVE_SUCCESS', model=model)
        return result
    except Exception as exc:
        record('Gemini', 'LIVE_FAILED', model=model, error=exc)
        raise
