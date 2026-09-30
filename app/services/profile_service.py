"""Doctor profile service — read and update doctor profile data."""

import logging
from app.extensions import sb

logger = logging.getLogger('tunes_pharma.profile')

SAFE_FIELDS = {
    'id', 'name', 'username', 'email', 'phone', 'hospital', 'specialty',
    'whatsapp_number', 'whatsapp_consent', 'is_active', 'created_at',
}

UPDATABLE_FIELDS = {'name', 'specialty', 'hospital', 'email', 'phone', 'whatsapp_number'}

PREFERENCE_FIELDS = {'email_preference', 'push_preference', 'sms_preference'}


def get_profile(doctor_id):
    if not sb:
        return None

    try:
        result = sb.table('doctors').select('*').eq('id', doctor_id).execute()
        if not result.data:
            return None
        return _sanitize(result.data[0])
    except Exception as e:
        logger.error(f"get_profile error: {e}")
        return None


def update_profile(doctor_id, updates):
    if not sb:
        return None, 'Database unavailable.'

    clean = {k: v for k, v in updates.items() if k in UPDATABLE_FIELDS}
    if not clean:
        return None, 'No valid fields to update.'

    try:
        result = (sb.table('doctors')
                  .update(clean)
                  .eq('id', doctor_id)
                  .execute())
        if result.data:
            return _sanitize(result.data[0]), None
        return None, 'Update failed.'
    except Exception as e:
        logger.error(f"update_profile error: {e}")
        return None, str(e)


def get_notification_preferences(doctor_id):
    if not sb:
        return None

    try:
        result = (sb.table('doctors')
                  .select('email_preference, push_preference, sms_preference')
                  .eq('id', doctor_id)
                  .execute())
        if not result.data:
            return None
        row = result.data[0]
        return {
            'email_preference': row.get('email_preference', True),
            'push_preference': row.get('push_preference', True),
            'sms_preference': row.get('sms_preference', False),
        }
    except Exception as e:
        logger.error(f"get_notification_preferences error: {e}")
        return None


def update_notification_preferences(doctor_id, updates):
    if not sb:
        return None, 'Database unavailable.'

    clean = {}
    for k, v in updates.items():
        if k in PREFERENCE_FIELDS:
            if not isinstance(v, bool):
                return None, f'{k} must be a boolean.'
            clean[k] = v

    if not clean:
        return None, 'No valid preference fields to update.'

    try:
        result = (sb.table('doctors')
                  .update(clean)
                  .eq('id', doctor_id)
                  .execute())
        if result.data:
            row = result.data[0]
            return {
                'email_preference': row.get('email_preference', True),
                'push_preference': row.get('push_preference', True),
                'sms_preference': row.get('sms_preference', False),
            }, None
        return None, 'Update failed.'
    except Exception as e:
        logger.error(f"update_notification_preferences error: {e}")
        return None, str(e)


def _sanitize(doctor):
    return {k: doctor.get(k) for k in SAFE_FIELDS if k in doctor}
