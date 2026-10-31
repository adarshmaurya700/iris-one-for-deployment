"""Backward-compatible chat contract using the same scoped catalog as Ask IRIS."""
from ai_assistant import DEFAULT_QUICK_PROMPTS, ask_local_cache
from application_service import student_identity


async def process_assistant_chat(message, history=None, student_profile=None, active_opportunity_id=None, db=None, current_user=None, **kwargs):
    result = await ask_local_cache(message, student_identity(current_user), db, active_opportunity_id, current_user)
    return {**result, 'reply': result['answer'], 'suggested_opportunities': result['matched_opportunities'][:2],
            'discovered_opportunity': None, 'quick_prompts': DEFAULT_QUICK_PROMPTS,
            'mode': 'fallback' if result['model_used'] == 'deterministic-local-rag' else 'live'}
