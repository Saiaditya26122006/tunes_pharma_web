"""Tunes Pharma application factory."""

import os
import logging
from flask import Flask
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / '.env', override=True)


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'),
    )

    from app.config import Config
    app.config.from_object(Config)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    # Context processor
    @app.context_processor
    def inject_base_url():
        return {'base_url': app.config['BASE_URL']}

    # Register blueprints
    from app.routes.public import public_bp
    from app.routes.admin import admin_bp
    from app.routes.api_v1 import api_v1_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_v1_bp, url_prefix='/api/v1')

    # CORS for API routes only
    cors_origins = app.config.get('CORS_ORIGINS', [])
    if cors_origins:
        try:
            from flask_cors import CORS
            CORS(app, resources={r"/api/*": {"origins": cors_origins}},
                 supports_credentials=True)
        except ImportError:
            logging.getLogger('tunes_pharma').warning("flask-cors not installed, CORS not configured")

    return app
