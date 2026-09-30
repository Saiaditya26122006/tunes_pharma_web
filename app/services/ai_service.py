"""AI service abstraction — wraps Anthropic/OpenRouter calls."""

import os
import logging

logger = logging.getLogger('tunes_pharma.ai')


def _get_anthropic_client():
    key = os.getenv('ANTHROPIC_API_KEY')
    if not key:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=key)
    except Exception as e:
        logger.error(f"Anthropic client init error: {e}")
        return None


def generate_completion(system_prompt: str, user_message: str,
                        model: str = 'claude-sonnet-4-6', max_tokens: int = 1024):
    """Send a prompt to the AI provider and return the response text.

    Returns (text, None) on success or (None, error_message) on failure.
    """
    client = _get_anthropic_client()
    if not client:
        return None, 'AI service not configured. Contact your administrator.'
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{'role': 'user', 'content': user_message}],
        )
        return resp.content[0].text, None
    except Exception as e:
        logger.error(f"AI completion error: {e}")
        return None, f'AI service error: {e}'
