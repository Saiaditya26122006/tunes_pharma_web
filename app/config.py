import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        if os.getenv('FLASK_DEBUG', 'false').lower() == 'true':
            import secrets
            SECRET_KEY = secrets.token_hex(32)
        else:
            raise RuntimeError(
                "SECRET_KEY must be set in production. "
                "Set the SECRET_KEY environment variable."
            )

    UPLOAD_FOLDER = '/tmp/uploads'
    BASE_URL = os.getenv('BASE_URL', 'https://tunespharma.org')

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_ALGORITHM = 'HS256'

    # Rate limiting (Supabase-backed for serverless compatibility)
    RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
    RATE_LIMIT_LOGIN_MAX = int(os.getenv('RATE_LIMIT_LOGIN_MAX', '5'))
    RATE_LIMIT_LOGIN_WINDOW_SECONDS = int(os.getenv('RATE_LIMIT_LOGIN_WINDOW', '300'))
    RATE_LIMIT_API_MAX = int(os.getenv('RATE_LIMIT_API_MAX', '60'))
    RATE_LIMIT_API_WINDOW_SECONDS = int(os.getenv('RATE_LIMIT_API_WINDOW', '60'))

    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',') if os.getenv('CORS_ORIGINS') else []

    # Legacy admin password (kept during migration, will be deprecated)
    LEGACY_ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
