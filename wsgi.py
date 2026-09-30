"""Entry point — exposes `app` for Vercel and local dev.

Vercel's @vercel/python runtime expects a module-level `app` object.
All application logic lives in the `app` package (app/__init__.py).
"""

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=app.config.get('DEBUG', False))
