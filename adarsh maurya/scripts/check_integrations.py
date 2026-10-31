"""One controlled provider probe. No DB writes, retries, wallet guesses or key output."""
import argparse
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from catalog import utc_now
from runtime_config import credential, mode
from diagnostics import snapshot, record


async def run(live=False):
    evidence = {'checked_at': utc_now(), 'operating_mode': mode(), 'verification_claimed': False}
    if not live:
        return {**evidence, 'note': 'No network calls made. Use --live for at most one Gemini and one Search/Fetch/Agent operation.', **snapshot()}
    if credential('GEMINI_API_KEY') and mode() == 'live':
        from providers import gemini_generate
        try:
            result = await gemini_generate('Return JSON with status exactly ok. Do not include any other facts.', 'Connectivity test.', json_output=True, max_tokens=80)
            evidence['Gemini'] = {'status': 'Working' if result == {'status': 'ok'} else 'Failed', 'diagnostic_status': 'LIVE_SUCCESS', 'model': __import__('os').environ.get('GEMINI_MODEL','gemini-2.5-flash')}
        except Exception as exc:
            evidence['Gemini'] = {'status': 'Failed', 'error_type': type(exc).__name__}
    else:
        evidence['Gemini'] = {'status': 'Not configured', 'live_test': 'Untested'}
    if credential('TINYFISH_API_KEY') and mode() == 'live':
        from tinyfish_pipeline import tinysearch, tinyfetch, tinyagent
        url = 'https://bhartiairtelfoundation.org/bharti-airtel-scholarship'
        try:
            search = await tinysearch('Bharti Airtel Foundation scholarship official portal')
            evidence['TinySearch'] = {'status': 'Working', 'result_count': len(search['results'])}
            page = await tinyfetch(url)
            evidence['TinyFetch'] = {'status': 'Working', 'characters': len(page['markdown'])}
            agent = await tinyagent(url, 'Read this official scholarship page. Do not sign in, submit forms or bypass restrictions. Return JSON containing is_button_live (boolean or null), application_url and evidence. Set true only if a current application action is visibly open; false if closed; null if uncertain.')
            evidence['TinyAgent'] = {'status': 'Working', 'run_status': agent['status'], 'button_state': agent['result'].get('is_button_live')}
            record('TinyFish', 'LIVE_SUCCESS')
            evidence['TinyFish'] = {'status': 'Working', 'full_verification': 'Untested without Gemini and validated program extraction'}
        except Exception as exc:
            record('TinyFish', 'LIVE_FAILED', error=exc)
            evidence['TinyFish'] = {'status': 'Failed', 'error_type': type(exc).__name__, 'http_status': getattr(getattr(exc,'response',None),'status_code',None)}
    else:
        evidence['TinyFish'] = {'status': 'Not configured', 'live_test': 'Untested'}
    return {**evidence, 'diagnostics': snapshot()}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--output', type=Path)
    args=parser.parse_args()
    data=asyncio.run(run(args.live))
    output=json.dumps(data, indent=2)
    if args.output:
        args.output.write_text(output,encoding='utf-8')
    print(output)
