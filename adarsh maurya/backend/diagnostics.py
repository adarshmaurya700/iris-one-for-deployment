"""Process-local, redacted operational evidence; never store prompts or credentials."""
import logging
import threading
from catalog import utc_now
from runtime_config import credential, mode

STATES = {'LIVE_SUCCESS', 'LIVE_FAILED', 'CACHED_RESULT', 'LOCAL_FALLBACK', 'NOT_CONFIGURED'}
_lock = threading.Lock()
_events = {}
log = logging.getLogger('iris.integrations')


def record(service, status, *, model=None, error=None):
    if status not in STATES:
        raise ValueError('Unknown diagnostic state')
    # Exception messages/URLs can contain API keys, student resumes or upstream bodies.
    code = type(error).__name__ if error else None
    http_status = getattr(getattr(error, 'response', None), 'status_code', None)
    with _lock:
        _events[service] = {'status': status, 'checked_at': utc_now(), 'model': model,
                            'error_type': code, 'http_status': http_status}
    if error:
        log.warning('%s failed (%s, HTTP %s)', service, code, http_status or 'n/a')


def snapshot():
    with _lock:
        data = {key: dict(value) for key, value in _events.items()}
    for service, key in [('Gemini', 'GEMINI_API_KEY'), ('TinyFish', 'TINYFISH_API_KEY'), ('Groq', 'GROQ_API_KEY'), ('Ollama', 'OLLAMA_BASE_URL')]:
        configured = bool(credential(key))
        item = data.setdefault(service, {'status': 'CACHED_RESULT' if mode() == 'demo' else 'NOT_CONFIGURED' if not configured else 'UNTESTED'})
        item['configured'] = configured
    return {'operating_mode': mode(), 'scope': 'This server process; configured does not mean tested.', 'services': data}
