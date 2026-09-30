"""Push token registration service — Expo push tokens for mobile."""

import logging
import re
from datetime import datetime, timezone
from app.extensions import sb

logger = logging.getLogger('tunes_pharma.push')

EXPO_TOKEN_PATTERN = re.compile(r'^ExponentPushToken\[.+\]$')


def subscribe(doctor_id, expo_token, platform=None):
    if not sb:
        return None, 'Database unavailable.'

    if not expo_token or not EXPO_TOKEN_PATTERN.match(expo_token):
        return None, 'Invalid Expo push token format.'

    if platform and platform not in ('ios', 'android', 'web'):
        return None, 'Invalid platform. Must be ios, android, or web.'

    try:
        existing = (sb.table('push_subscriptions')
                    .select('id, doctor_id')
                    .eq('expo_token', expo_token)
                    .execute())
        if existing.data:
            row = existing.data[0]
            if row['doctor_id'] != doctor_id:
                return None, 'Token registered to another account.'
            sb.table('push_subscriptions').update({
                'platform': platform,
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }).eq('id', row['id']).execute()
            return row, 'already_exists'

        result = (sb.table('push_subscriptions')
                  .insert({
                      'doctor_id': doctor_id,
                      'subscription_json': {'expo_token': expo_token},
                      'expo_token': expo_token,
                      'platform': platform,
                      'updated_at': datetime.now(timezone.utc).isoformat(),
                  })
                  .execute())
        if result.data:
            return result.data[0], None
        return None, 'Insert failed.'
    except Exception as e:
        logger.error(f"subscribe error: {e}")
        return None, str(e)


def unsubscribe(doctor_id, expo_token):
    if not sb:
        return False

    if not expo_token:
        return False

    try:
        result = (sb.table('push_subscriptions')
                  .delete()
                  .eq('doctor_id', doctor_id)
                  .eq('expo_token', expo_token)
                  .execute())
        return bool(result.data)
    except Exception as e:
        logger.error(f"unsubscribe error: {e}")
        return False
