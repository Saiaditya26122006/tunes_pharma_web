"""Shared application state — Supabase client and external service handles."""

import os
import logging

logger = logging.getLogger('tunes_pharma')

# Supabase client (initialized once at import time)
sb = None
_sb_error = None

try:
    from supabase_client import supabase as _sb, supabase_error as _sb_err
    sb = _sb
    _sb_error = _sb_err
except Exception as e:
    _sb_error = str(e)

# Notification engine
ne = None
try:
    import notification_engine as _ne
    ne = _ne
except Exception:
    pass

# WhatsApp service
wa = None
try:
    import whatsapp_service as _wa
    wa = _wa
except Exception:
    pass

# OpenAI client (optional)
openai_client = None
try:
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        from openai import OpenAI
        openai_client = OpenAI(api_key=api_key)
except Exception as e:
    logger.warning(f"Could not initialize OpenAI client: {e}")
