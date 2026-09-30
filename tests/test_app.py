"""Tests for the Tunes Pharma modular Flask application.

Run with:  python -m pytest tests/ -v
"""

import os
import json
import pytest

os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-pytest')
os.environ.setdefault('JWT_SECRET_KEY', 'test-jwt-secret-for-pytest')

from app import create_app


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


# ── Smoke tests: app bootstrap ────────────────────────────────────

class TestAppBootstrap:
    def test_create_app_returns_flask(self, app):
        assert app is not None
        assert app.config['TESTING'] is True

    def test_routes_registered(self, app):
        rules = [r.rule for r in app.url_map.iter_rules()]
        assert '/' in rules
        assert '/about' in rules
        assert '/api/v1/auth/login' in rules
        assert '/api/v1/articles' in rules

    def test_api_prefix(self, app):
        rules = [r.rule for r in app.url_map.iter_rules() if r.rule.startswith('/api/v1')]
        assert len(rules) >= 6


# ── Public routes ─────────────────────────────────────────────────

class TestPublicRoutes:
    def test_home(self, client):
        resp = client.get('/')
        assert resp.status_code == 200

    def test_about(self, client):
        resp = client.get('/about')
        assert resp.status_code == 200

    def test_contact(self, client):
        resp = client.get('/contact')
        assert resp.status_code == 200

    def test_products(self, client):
        resp = client.get('/products')
        assert resp.status_code == 200

    def test_product_detail_existing(self, client):
        resp = client.get('/products/ecoglim-mv1')
        assert resp.status_code == 200

    def test_product_detail_missing(self, client):
        resp = client.get('/products/nonexistent-product')
        assert resp.status_code == 404

    def test_gallery(self, client):
        resp = client.get('/gallery')
        assert resp.status_code == 200

    def test_gallery_redirect(self, client):
        resp = client.get('/Gallery')
        assert resp.status_code == 308

    def test_set_language(self, client):
        resp = client.get('/set-language/hi', follow_redirects=False)
        assert resp.status_code == 302

    def test_robots_txt(self, client):
        resp = client.get('/robots.txt')
        assert resp.status_code == 200
        assert b'User-agent' in resp.data

    def test_sitemap_xml(self, client):
        resp = client.get('/sitemap.xml')
        assert resp.status_code == 200
        assert b'urlset' in resp.data

    def test_product_catalog(self, client):
        resp = client.get('/product-catalog')
        assert resp.status_code == 200

    def test_stockist_locator(self, client):
        resp = client.get('/stockist-locator')
        assert resp.status_code == 200


# ── API v1: auth (no DB) ─────────────────────────────────────────

class TestAuthAPI:
    def test_login_no_body(self, client):
        resp = client.post('/api/v1/auth/login', content_type='application/json')
        data = json.loads(resp.data)
        assert resp.status_code == 400
        assert data['success'] is False
        assert data['error']['code'] == 'BAD_REQUEST'

    def test_login_missing_fields(self, client):
        resp = client.post('/api/v1/auth/login',
                           json={'username': 'test'},
                           content_type='application/json')
        data = json.loads(resp.data)
        assert resp.status_code == 400

    def test_login_invalid_credentials(self, client):
        resp = client.post('/api/v1/auth/login',
                           json={'username': 'nobody', 'password': 'wrong'},
                           content_type='application/json')
        data = json.loads(resp.data)
        assert resp.status_code == 401
        assert data['error']['code'] == 'UNAUTHORIZED'

    def test_refresh_no_body(self, client):
        resp = client.post('/api/v1/auth/refresh', content_type='application/json')
        data = json.loads(resp.data)
        assert resp.status_code == 400

    def test_me_no_token(self, client):
        resp = client.get('/api/v1/auth/me')
        data = json.loads(resp.data)
        assert resp.status_code == 401
        assert data['error']['code'] == 'UNAUTHORIZED'

    def test_me_bad_token(self, client):
        resp = client.get('/api/v1/auth/me',
                          headers={'Authorization': 'Bearer invalid-token'})
        data = json.loads(resp.data)
        assert resp.status_code == 401

    def test_logout_no_token(self, client):
        resp = client.post('/api/v1/auth/logout', content_type='application/json')
        data = json.loads(resp.data)
        assert resp.status_code == 401


# ── API v1: articles (no DB) ─────────────────────────────────────

class TestArticlesAPI:
    def test_articles_list_no_token(self, client):
        resp = client.get('/api/v1/articles')
        data = json.loads(resp.data)
        assert resp.status_code == 401

    def test_articles_detail_no_token(self, client):
        resp = client.get('/api/v1/articles/some-uuid')
        data = json.loads(resp.data)
        assert resp.status_code == 401


# ── Admin routes ──────────────────────────────────────────────────

class TestAdminRoutes:
    def test_admin_login_page(self, client):
        resp = client.get('/admin')
        assert resp.status_code == 200

    def test_admin_dashboard_requires_auth(self, client):
        resp = client.get('/admin/dashboard', follow_redirects=False)
        assert resp.status_code == 302

    def test_admin_papers_requires_auth(self, client):
        resp = client.get('/admin/papers', follow_redirects=False)
        assert resp.status_code == 302

    def test_admin_doctors_requires_auth(self, client):
        resp = client.get('/admin/doctors', follow_redirects=False)
        assert resp.status_code == 302


# ── Response format helpers ───────────────────────────────────────

class TestResponseHelpers:
    def test_success_response_format(self, app):
        from app.utils.responses import success_response
        with app.test_request_context():
            resp, status = success_response({'key': 'val'})
            data = json.loads(resp.data)
            assert status == 200
            assert data['success'] is True
            assert data['data']['key'] == 'val'

    def test_error_response_format(self, app):
        from app.utils.responses import error_response
        with app.test_request_context():
            resp, status = error_response('TEST_ERR', 'A message', 422)
            data = json.loads(resp.data)
            assert status == 422
            assert data['success'] is False
            assert data['error']['code'] == 'TEST_ERR'

    def test_pagination_builder(self):
        from app.utils.responses import build_pagination
        p = build_pagination(1, 20, 50)
        assert p['page'] == 1
        assert p['total'] == 50
        assert p['has_next'] is True

        p2 = build_pagination(3, 20, 50)
        assert p2['has_next'] is False


# ── Data module ───────────────────────────────────────────────────

class TestAppData:
    def test_products_data_loaded(self):
        from app_data import products_data
        assert 'ecoglim-mv1' in products_data
        assert len(products_data) == 8

    def test_stockists_data_loaded(self):
        from app_data import stockists_data
        assert len(stockists_data) == 5

    def test_translations_loaded(self):
        from app_data import translations
        assert 'en' in translations
        assert 'hi' in translations
        assert translations['en']['home'] == 'Home'

    def test_regulatory_data_loaded(self):
        from app_data import regulatory_data
        assert 'certifications' in regulatory_data
        assert 'approvals' in regulatory_data


# ── Security tests ────────────────────────────────────────────────

class TestSecurityConfig:
    def test_secret_key_required_in_production(self):
        old = os.environ.pop('SECRET_KEY', None)
        old_debug = os.environ.get('FLASK_DEBUG')
        os.environ['FLASK_DEBUG'] = 'false'
        try:
            with pytest.raises(RuntimeError, match="SECRET_KEY must be set"):
                from importlib import reload
                import app.config
                reload(app.config)
        finally:
            if old:
                os.environ['SECRET_KEY'] = old
            if old_debug is not None:
                os.environ['FLASK_DEBUG'] = old_debug
            else:
                os.environ.pop('FLASK_DEBUG', None)

    def test_jwt_secret_required_in_production(self):
        old_jwt = os.environ.pop('JWT_SECRET_KEY', None)
        old_sk = os.environ.pop('SECRET_KEY', None)
        old_debug = os.environ.get('FLASK_DEBUG')
        os.environ['FLASK_DEBUG'] = 'false'
        try:
            from app.services.auth_service import _jwt_secret
            with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
                _jwt_secret()
        finally:
            if old_jwt:
                os.environ['JWT_SECRET_KEY'] = old_jwt
            if old_sk:
                os.environ['SECRET_KEY'] = old_sk
            if old_debug is not None:
                os.environ['FLASK_DEBUG'] = old_debug
            else:
                os.environ.pop('FLASK_DEBUG', None)

    def test_admin_debug_requires_auth(self, client):
        resp = client.get('/admin/debug', follow_redirects=False)
        assert resp.status_code == 302

    def test_expired_jwt_rejected(self, app):
        import jwt as pyjwt
        from datetime import datetime, timezone, timedelta
        token = pyjwt.encode(
            {'sub': 'fake-id', 'type': 'access',
             'exp': datetime.now(timezone.utc) - timedelta(seconds=10)},
            os.environ['JWT_SECRET_KEY'], algorithm='HS256')
        with app.test_client() as c:
            resp = c.get('/api/v1/auth/me',
                         headers={'Authorization': f'Bearer {token}'})
            assert resp.status_code == 401

    def test_refresh_token_as_access_rejected(self, app):
        import jwt as pyjwt
        from datetime import datetime, timezone, timedelta
        token = pyjwt.encode(
            {'sub': 'fake-id', 'type': 'refresh',
             'exp': datetime.now(timezone.utc) + timedelta(hours=1)},
            os.environ['JWT_SECRET_KEY'], algorithm='HS256')
        with app.test_client() as c:
            resp = c.get('/api/v1/auth/me',
                         headers={'Authorization': f'Bearer {token}'})
            assert resp.status_code == 401
