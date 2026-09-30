"""Authentication service — JWT tokens and password verification."""

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta

import jwt
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import sb

logger = logging.getLogger('tunes_pharma.auth')

# ------------------------------------------------------------------
# Configuration (read once)
# ------------------------------------------------------------------

def _jwt_secret():
    secret = os.getenv('JWT_SECRET_KEY') or os.getenv('SECRET_KEY') or ''
    if not secret:
        if os.getenv('FLASK_DEBUG', 'false').lower() == 'true':
            logger.warning("JWT_SECRET_KEY not set — using insecure dev fallback")
            return 'insecure-dev-only-key'
        raise RuntimeError(
            "JWT_SECRET_KEY (or SECRET_KEY) must be set in production. "
            "Set the JWT_SECRET_KEY environment variable."
        )
    return secret

_ACCESS_EXPIRY = timedelta(minutes=15)
_REFRESH_EXPIRY = timedelta(days=30)
_ALGORITHM = 'HS256'


# ------------------------------------------------------------------
# Doctor authentication (JWT for mobile/API clients)
# ------------------------------------------------------------------

def authenticate_doctor(username: str, password: str):
    """Validate credentials and return doctor record or None."""
    if not sb or not username or not password:
        return None
    try:
        result = sb.table('doctors').select('*').eq('username', username).execute()
        if not result.data:
            return None
        doctor = result.data[0]
        if not doctor.get('is_active', False):
            return None
        if not check_password_hash(doctor['password_hash'], password):
            return None
        return doctor
    except Exception as e:
        logger.error(f"Doctor auth error: {e}")
        return None


def create_token_pair(doctor):
    """Issue access + refresh tokens for an authenticated doctor."""
    now = datetime.now(timezone.utc)
    doctor_id = doctor['id']

    access_payload = {
        'sub': doctor_id,
        'name': doctor.get('name', ''),
        'type': 'access',
        'iat': now,
        'exp': now + _ACCESS_EXPIRY,
    }
    access_token = jwt.encode(access_payload, _jwt_secret(), algorithm=_ALGORITHM)

    refresh_jti = str(uuid.uuid4())
    refresh_payload = {
        'sub': doctor_id,
        'type': 'refresh',
        'jti': refresh_jti,
        'iat': now,
        'exp': now + _REFRESH_EXPIRY,
    }
    refresh_token = jwt.encode(refresh_payload, _jwt_secret(), algorithm=_ALGORITHM)

    _store_refresh_token(doctor_id, refresh_jti, now + _REFRESH_EXPIRY)

    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires_in': int(_ACCESS_EXPIRY.total_seconds()),
        'token_type': 'Bearer',
    }


def decode_access_token(token: str):
    """Decode and validate an access token. Returns payload dict or None."""
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[_ALGORITHM])
        if payload.get('type') != 'access':
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def refresh_access_token(refresh_token_str: str):
    """Validate refresh token, revoke it, and issue a new pair (rotation)."""
    try:
        payload = jwt.decode(refresh_token_str, _jwt_secret(), algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None, 'Refresh token expired.'
    except jwt.InvalidTokenError:
        return None, 'Invalid refresh token.'

    if payload.get('type') != 'refresh':
        return None, 'Invalid token type.'

    jti = payload.get('jti')
    doctor_id = payload.get('sub')

    if not _validate_and_revoke_refresh_token(doctor_id, jti):
        return None, 'Token already used or revoked.'

    # Fetch doctor to confirm still active
    if not sb:
        return None, 'Database unavailable.'
    try:
        result = sb.table('doctors').select('*').eq('id', doctor_id).execute()
        if not result.data or not result.data[0].get('is_active', False):
            return None, 'Account inactive.'
    except Exception:
        return None, 'Database error.'

    return create_token_pair(result.data[0]), None


def revoke_refresh_token(refresh_token_str: str):
    """Explicitly revoke a refresh token (logout)."""
    try:
        payload = jwt.decode(refresh_token_str, _jwt_secret(), algorithms=[_ALGORITHM])
        jti = payload.get('jti')
        doctor_id = payload.get('sub')
        if jti and doctor_id:
            _validate_and_revoke_refresh_token(doctor_id, jti)
    except jwt.InvalidTokenError:
        pass


# ------------------------------------------------------------------
# Admin authentication (session-based, for admin panel)
# ------------------------------------------------------------------

def authenticate_admin(email: str, password: str):
    """Validate admin credentials against admin_users table.

    Returns admin user dict or None.
    """
    if not sb or not email or not password:
        return None
    try:
        result = (sb.table('admin_users')
                  .select('*')
                  .eq('email', email)
                  .eq('is_active', True)
                  .execute())
        if not result.data:
            return None
        admin = result.data[0]
        if not check_password_hash(admin['password_hash'], password):
            return None
        # Update last_login_at
        sb.table('admin_users').update({
            'last_login_at': datetime.now(timezone.utc).isoformat()
        }).eq('id', admin['id']).execute()
        return admin
    except Exception as e:
        logger.error(f"Admin auth error: {e}")
        return None


def create_admin_user(email: str, password: str, name: str, role: str = 'admin'):
    """Create a new admin user. Returns the record or None."""
    if not sb:
        return None
    try:
        result = sb.table('admin_users').insert({
            'email': email,
            'password_hash': generate_password_hash(password),
            'name': name,
            'role': role,
            'is_active': True,
        }).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Create admin error: {e}")
        return None


# ------------------------------------------------------------------
# Rate limiting (Supabase-backed, serverless-compatible)
# ------------------------------------------------------------------

def check_rate_limit(identifier: str, action: str, max_attempts: int, window_seconds: int) -> bool:
    """Return True if the request is within limits, False if rate-limited.

    Uses the ``rate_limits`` table in Supabase to persist counters across
    serverless invocations.
    """
    if not sb:
        return True  # fail open if DB unavailable
    try:
        now = datetime.now(timezone.utc)
        window_start = (now - timedelta(seconds=window_seconds)).isoformat()
        key = f"{action}:{identifier}"

        # Count recent attempts
        result = (sb.table('rate_limits')
                  .select('id', count='exact')
                  .eq('key', key)
                  .gte('created_at', window_start)
                  .execute())
        count = result.count if result.count is not None else len(result.data or [])

        if count >= max_attempts:
            return False

        # Record this attempt
        sb.table('rate_limits').insert({
            'key': key,
            'created_at': now.isoformat(),
        }).execute()
        return True
    except Exception as e:
        logger.error(f"Rate limit check error: {e}")
        return True  # fail open


# ------------------------------------------------------------------
# Refresh token persistence
# ------------------------------------------------------------------

def _store_refresh_token(doctor_id: str, jti: str, expires_at: datetime):
    if not sb:
        return
    try:
        sb.table('refresh_tokens').insert({
            'doctor_id': doctor_id,
            'jti': jti,
            'expires_at': expires_at.isoformat(),
        }).execute()
    except Exception as e:
        logger.error(f"Store refresh token error: {e}")


def _validate_and_revoke_refresh_token(doctor_id: str, jti: str) -> bool:
    """Check that the refresh token exists and has not been revoked, then revoke it.

    Returns True if token was valid and is now revoked.
    """
    if not sb or not jti:
        return False
    try:
        result = (sb.table('refresh_tokens')
                  .select('id')
                  .eq('doctor_id', doctor_id)
                  .eq('jti', jti)
                  .eq('revoked', False)
                  .execute())
        if not result.data:
            return False
        sb.table('refresh_tokens').update({
            'revoked': True,
        }).eq('id', result.data[0]['id']).execute()
        return True
    except Exception as e:
        logger.error(f"Revoke refresh token error: {e}")
        return False
