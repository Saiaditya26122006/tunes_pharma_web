"""Authentication decorators for admin (session) and doctor (JWT) access."""

from functools import wraps
from flask import session, redirect, request, g
from app.utils.responses import error_response
from app.services.auth_service import decode_access_token


def admin_required(f):
    """Require an authenticated admin session (website/admin panel)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin') and not session.get('admin_user_id'):
            return redirect('/admin')
        return f(*args, **kwargs)
    return decorated


def doctor_required(f):
    """Require a valid JWT access token (API endpoints).

    Sets ``g.doctor_id`` from the verified token — route handlers should
    use this instead of trusting any client-supplied doctor ID.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return error_response('UNAUTHORIZED', 'Authentication required.', 401)

        token = auth_header[7:]
        payload = decode_access_token(token)
        if payload is None:
            return error_response('UNAUTHORIZED', 'Invalid or expired token.', 401)

        g.doctor_id = payload['sub']
        g.doctor_name = payload.get('name', '')
        return f(*args, **kwargs)
    return decorated
