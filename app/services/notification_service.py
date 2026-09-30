"""Thin wrapper around the existing notification_engine and whatsapp_service.

Does NOT rewrite any notification logic — just provides a clean import boundary
so route files don't reach into the engine internals.
"""

import logging
from app.extensions import sb, ne, wa

logger = logging.getLogger('tunes_pharma.notifications')


def send_email_notification(**kwargs):
    """Delegate to notification_engine.send_email_notification."""
    if ne:
        return ne.send_email_notification(**kwargs)
    logger.warning("Notification engine not available for email")
    return False


def trigger_notifications(message_type, channel, target_doctors,
                          article_data=None, manual_message=None):
    """Delegate to notification_engine.trigger_notifications."""
    if ne:
        ne.trigger_notifications(sb, message_type, channel, target_doctors,
                                 article_data, manual_message)
    else:
        logger.warning("Notification engine not available")


def broadcast_whatsapp(doctors, article):
    """Delegate to whatsapp_service.broadcast_article_notification."""
    if wa and wa._is_configured():
        return wa.broadcast_article_notification(doctors, article)
    return None


def is_whatsapp_configured():
    return wa is not None and wa._is_configured()
