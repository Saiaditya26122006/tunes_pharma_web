"""
WhatsApp Business API notification service for Tunes Pharma.

Supports:
- Sending template messages via Meta WhatsApp Business API
- Automatic article notifications
- Manual admin messages
- Delivery tracking

Environment variables required:
  WHATSAPP_API_TOKEN   — Meta WhatsApp Business API bearer token
  WHATSAPP_PHONE_ID    — WhatsApp Business phone number ID
  WHATSAPP_TEMPLATE_NS — Template namespace (optional, for template messages)

The service is designed to be swappable — you can replace the
implementation with any other WhatsApp provider (e.g., Twilio,
Gupshup, WATI) by modifying the send_single_message function.
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone


# ── Configuration ──────────────────────────────────────────────

API_TOKEN = os.getenv("WHATSAPP_API_TOKEN", "")
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
TEMPLATE_NAMESPACE = os.getenv("WHATSAPP_TEMPLATE_NS", "")
BASE_URL = os.getenv("BASE_URL", "https://tunespharma.org")
WHATSAPP_API = f"https://graph.facebook.com/v18.0/{PHONE_ID}/messages"


def _is_configured():
    """Check if WhatsApp API credentials are configured."""
    return bool(API_TOKEN and PHONE_ID)


def send_single_message(phone_number, message_text):
    """
    Send a free-form text message to a single phone number.
    
    Note: Free-form messages are only allowed within the 24-hour
    customer service window. For messages outside this window,
    use send_template_message instead.
    
    Args:
        phone_number: Recipient phone number (with country code, e.g. "919876543210")
        message_text: Plain text message body
        
    Returns:
        dict with 'success' (bool), 'error' (str or None), 'response' (dict or None)
    """
    if not _is_configured():
        return {"success": False, "error": "WhatsApp API not configured", "response": None}
    
    # Normalize phone number (remove +, spaces, dashes)
    phone = phone_number.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message_text}
    }
    
    return _make_api_request(payload)


def send_template_message(phone_number, template_name, language_code="en", parameters=None):
    """
    Send a pre-approved template message. Required for outbound
    messages outside the 24-hour customer service window.
    
    Args:
        phone_number: Recipient phone number (with country code)
        template_name: Name of the approved template
        language_code: Language code (default: "en")
        parameters: List of parameter values for the template
        
    Returns:
        dict with 'success' (bool), 'error' (str or None), 'response' (dict or None)
    """
    if not _is_configured():
        return {"success": False, "error": "WhatsApp API not configured", "response": None}
    
    phone = phone_number.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    template_body = {"name": template_name, "language": {"code": language_code}}
    if parameters:
        template_body["components"] = [{"type": "body", "parameters": parameters}]
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": template_body
    }
    
    return _make_api_request(payload)


def send_article_notification(phone_number, doctor_name, article_title, article_description, article_url):
    """
    Send an article notification message to a doctor.
    
    Tries template message first (if template is configured),
    falls back to free-form text.
    """
    if not _is_configured():
        return {"success": False, "error": "WhatsApp API not configured", "response": None}
    
    if TEMPLATE_NAMESPACE:
        # Use pre-approved template
        params = [
            {"type": "text", "text": doctor_name},
            {"type": "text", "text": article_title},
            {"type": "text", "text": article_description or "A new academic resource has been published."},
            {"type": "text", "text": article_url}
        ]
        return send_template_message(phone_number, "article_notification", "en", params)
    else:
        # Free-form message (works within 24h window)
        message = (
            f"📋 *New Academic Insight Published*\n\n"
            f"Dear {doctor_name},\n\n"
            f"A new academic article has been published on Tunes Pharma:\n\n"
            f"*{article_title}*\n"
            f"{article_description or ''}\n\n"
            f"📖 Read the article:\n{article_url}\n\n"
            f"— Team Tunes Pharma"
        )
        return send_single_message(phone_number, message)


def send_manual_message(phone_number, message_text):
    """
    Send a manual/admin message to a doctor's WhatsApp.
    This is a simple text message wrapper.
    """
    return send_single_message(phone_number, message_text)


def _make_api_request(payload):
    """Make an HTTP request to the WhatsApp Business API."""
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            WHATSAPP_API,
            data=data,
            headers={
                "Authorization": f"Bearer {API_TOKEN}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))
            return {"success": True, "error": None, "response": response_data}
    
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass
        return {
            "success": False,
            "error": f"HTTP {e.code}: {error_body[:500]}",
            "response": None
        }
    except Exception as e:
        return {"success": False, "error": str(e), "response": None}


def broadcast_article_notification(doctors, article):
    """
    Send article notification to a list of eligible doctors.
    
    Args:
        doctors: List of doctor dicts with 'id', 'name', 'whatsapp_number' keys
        article: Dict with 'id', 'title', 'description', 'file_url' keys
        
    Returns:
        dict with delivery stats and per-recipient results
    """
    results = []
    success_count = 0
    fail_count = 0
    
    article_url = article.get("file_url", f"{BASE_URL}/research")
    
    for doctor in doctors:
        phone = doctor.get("whatsapp_number", "")
        if not phone:
            results.append({
                "doctor_id": doctor["id"],
                "doctor_name": doctor.get("name", "Unknown"),
                "status": "skipped",
                "error": "No WhatsApp number"
            })
            fail_count += 1
            continue
        
        result = send_article_notification(
            phone_number=phone,
            doctor_name=doctor.get("name", "Doctor"),
            article_title=article.get("title", "New Article"),
            article_description=article.get("description", ""),
            article_url=article_url
        )
        
        results.append({
            "doctor_id": doctor["id"],
            "doctor_name": doctor.get("name", "Unknown"),
            "whatsapp_number": phone,
            "status": "sent" if result["success"] else "failed",
            "error": result.get("error")
        })
        
        if result["success"]:
            success_count += 1
        else:
            fail_count += 1
    
    return {
        "total": len(doctors),
        "success": success_count,
        "failed": fail_count,
        "results": results
    }


def broadcast_manual_message(doctors, message_text):
    """
    Send a manual message to a list of doctors.
    
    Args:
        doctors: List of doctor dicts with 'id', 'name', 'whatsapp_number' keys
        message_text: The message content
        
    Returns:
        dict with delivery stats and per-recipient results
    """
    results = []
    success_count = 0
    fail_count = 0
    
    for doctor in doctors:
        phone = doctor.get("whatsapp_number", "")
        if not phone:
            results.append({
                "doctor_id": doctor["id"],
                "doctor_name": doctor.get("name", "Unknown"),
                "status": "skipped",
                "error": "No WhatsApp number"
            })
            fail_count += 1
            continue
        
        result = send_manual_message(phone, message_text)
        
        results.append({
            "doctor_id": doctor["id"],
            "doctor_name": doctor.get("name", "Unknown"),
            "whatsapp_number": phone,
            "status": "sent" if result["success"] else "failed",
            "error": result.get("error")
        })
        
        if result["success"]:
            success_count += 1
        else:
            fail_count += 1
    
    return {
        "total": len(doctors),
        "success": success_count,
        "failed": fail_count,
        "results": results
    }
