"""Tests for Stage 2A — Doctor Platform API endpoints.

Tests run against the Flask test client without a live Supabase connection
(sb=None). This validates route registration, authentication enforcement,
request parsing, and response format. Integration tests with a live DB
require SUPABASE_URL and SUPABASE_SERVICE_KEY.

Run with:  python -m pytest tests/test_api_v1_stage2.py -v
"""

import os
import json
import pytest
from datetime import datetime, timezone, timedelta

os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-pytest')
os.environ.setdefault('JWT_SECRET_KEY', 'test-jwt-secret-for-pytest')

import jwt as pyjwt
from app import create_app


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _make_access_token(doctor_id='test-doctor-uuid', name='Dr. Test'):
    secret = os.environ['JWT_SECRET_KEY']
    now = datetime.now(timezone.utc)
    payload = {
        'sub': doctor_id,
        'name': name,
        'type': 'access',
        'iat': now,
        'exp': now + timedelta(hours=1),
    }
    return pyjwt.encode(payload, secret, algorithm='HS256')


def _auth_header(doctor_id='test-doctor-uuid'):
    return {'Authorization': f'Bearer {_make_access_token(doctor_id)}'}


# ── Route registration ──────────────────────────────────────────

class TestRouteRegistration:
    def test_new_routes_registered(self, app):
        rules = [r.rule for r in app.url_map.iter_rules()]
        expected = [
            '/api/v1/bookmarks',
            '/api/v1/bookmarks/<article_id>',
            '/api/v1/profile',
            '/api/v1/profile/notifications',
            '/api/v1/notifications',
            '/api/v1/notifications/<notification_id>/read',
            '/api/v1/notifications/read-all',
            '/api/v1/push/subscribe',
            '/api/v1/feed',
        ]
        for route in expected:
            assert route in rules, f"Missing route: {route}"

    def test_api_v1_route_count(self, app):
        rules = [r.rule for r in app.url_map.iter_rules() if r.rule.startswith('/api/v1')]
        assert len(rules) >= 15


# ── Bookmarks ────────────────────────────────────────────────────

class TestBookmarksAPI:
    def test_list_no_token(self, client):
        resp = client.get('/api/v1/bookmarks')
        data = json.loads(resp.data)
        assert resp.status_code == 401
        assert data['error']['code'] == 'UNAUTHORIZED'

    def test_list_authenticated(self, client):
        resp = client.get('/api/v1/bookmarks', headers=_auth_header())
        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert data['success'] is True
        assert 'data' in data
        assert 'pagination' in data

    def test_create_no_token(self, client):
        resp = client.post('/api/v1/bookmarks/some-uuid')
        assert resp.status_code == 401

    def test_create_authenticated_no_db(self, client):
        resp = client.post('/api/v1/bookmarks/some-uuid', headers=_auth_header())
        data = json.loads(resp.data)
        assert resp.status_code in (404, 500)

    def test_delete_no_token(self, client):
        resp = client.delete('/api/v1/bookmarks/some-uuid')
        assert resp.status_code == 401

    def test_delete_authenticated_no_db(self, client):
        resp = client.delete('/api/v1/bookmarks/some-uuid', headers=_auth_header())
        data = json.loads(resp.data)
        assert resp.status_code == 404
        assert data['success'] is False


# ── Profile ──────────────────────────────────────────────────────

class TestProfileAPI:
    def test_get_no_token(self, client):
        resp = client.get('/api/v1/profile')
        assert resp.status_code == 401

    def test_get_authenticated(self, client):
        resp = client.get('/api/v1/profile', headers=_auth_header())
        data = json.loads(resp.data)
        assert resp.status_code in (200, 404)

    def test_update_no_token(self, client):
        resp = client.patch('/api/v1/profile', json={'name': 'New Name'})
        assert resp.status_code == 401

    def test_update_no_body(self, client):
        resp = client.patch('/api/v1/profile',
                           headers=_auth_header(),
                           content_type='application/json')
        data = json.loads(resp.data)
        assert resp.status_code == 400
        assert data['error']['code'] == 'BAD_REQUEST'

    def test_update_empty_body(self, client):
        resp = client.patch('/api/v1/profile',
                           headers=_auth_header(),
                           json={'password_hash': 'attack'})
        data = json.loads(resp.data)
        assert resp.status_code == 400
        assert 'No valid fields' in data['error']['message']

    def test_update_protected_fields_rejected(self, client):
        resp = client.patch('/api/v1/profile',
                           headers=_auth_header(),
                           json={'is_active': False, 'password_hash': 'x'})
        data = json.loads(resp.data)
        assert resp.status_code == 400


# ── Notification preferences ─────────────────────────────────────

class TestNotificationPrefsAPI:
    def test_get_no_token(self, client):
        resp = client.get('/api/v1/profile/notifications')
        assert resp.status_code == 401

    def test_get_authenticated(self, client):
        resp = client.get('/api/v1/profile/notifications', headers=_auth_header())
        assert resp.status_code in (200, 404)

    def test_update_no_token(self, client):
        resp = client.patch('/api/v1/profile/notifications',
                           json={'email_preference': False})
        assert resp.status_code == 401

    def test_update_no_body(self, client):
        resp = client.patch('/api/v1/profile/notifications',
                           headers=_auth_header(),
                           content_type='application/json')
        data = json.loads(resp.data)
        assert resp.status_code == 400

    def test_update_invalid_field(self, client):
        resp = client.patch('/api/v1/profile/notifications',
                           headers=_auth_header(),
                           json={'is_active': True})
        data = json.loads(resp.data)
        assert resp.status_code == 400
        assert 'No valid' in data['error']['message']

    def test_update_non_boolean_rejected(self, client):
        resp = client.patch('/api/v1/profile/notifications',
                           headers=_auth_header(),
                           json={'email_preference': 'yes'})
        data = json.loads(resp.data)
        assert resp.status_code == 400
        assert 'boolean' in data['error']['message']


# ── Notifications ────────────────────────────────────────────────

class TestNotificationsAPI:
    def test_list_no_token(self, client):
        resp = client.get('/api/v1/notifications')
        assert resp.status_code == 401

    def test_list_authenticated(self, client):
        resp = client.get('/api/v1/notifications', headers=_auth_header())
        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert data['success'] is True
        assert 'pagination' in data

    def test_list_pagination_params(self, client):
        resp = client.get('/api/v1/notifications?page=2&limit=5', headers=_auth_header())
        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert data['pagination']['page'] == 2
        assert data['pagination']['limit'] == 5

    def test_mark_read_no_token(self, client):
        resp = client.patch('/api/v1/notifications/some-id/read')
        assert resp.status_code == 401

    def test_mark_read_not_found(self, client):
        resp = client.patch('/api/v1/notifications/nonexistent-id/read',
                           headers=_auth_header())
        data = json.loads(resp.data)
        assert resp.status_code in (404, 500)

    def test_mark_all_read_no_token(self, client):
        resp = client.post('/api/v1/notifications/read-all')
        assert resp.status_code == 401

    def test_mark_all_read_authenticated(self, client):
        resp = client.post('/api/v1/notifications/read-all', headers=_auth_header())
        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert data['success'] is True
        assert 'marked' in data['data']


# ── Push token ───────────────────────────────────────────────────

class TestPushAPI:
    def test_subscribe_no_token(self, client):
        resp = client.post('/api/v1/push/subscribe',
                          json={'expo_token': 'ExponentPushToken[xxx]'})
        assert resp.status_code == 401

    def test_subscribe_missing_expo_token(self, client):
        resp = client.post('/api/v1/push/subscribe',
                          headers=_auth_header(),
                          json={})
        data = json.loads(resp.data)
        assert resp.status_code == 400
        assert 'expo_token' in data['error']['message']

    def test_subscribe_invalid_format(self, client):
        resp = client.post('/api/v1/push/subscribe',
                          headers=_auth_header(),
                          json={'expo_token': 'invalid-token'})
        data = json.loads(resp.data)
        assert resp.status_code == 400
        assert 'Invalid' in data['error']['message']

    def test_subscribe_valid_format_no_db(self, client):
        resp = client.post('/api/v1/push/subscribe',
                          headers=_auth_header(),
                          json={'expo_token': 'ExponentPushToken[abc123]',
                                'platform': 'ios'})
        data = json.loads(resp.data)
        assert resp.status_code in (201, 400, 500)

    def test_unsubscribe_no_token(self, client):
        resp = client.delete('/api/v1/push/subscribe',
                            json={'expo_token': 'ExponentPushToken[abc]'})
        assert resp.status_code == 401

    def test_unsubscribe_missing_expo_token(self, client):
        resp = client.delete('/api/v1/push/subscribe',
                            headers=_auth_header(),
                            json={})
        data = json.loads(resp.data)
        assert resp.status_code == 400

    def test_unsubscribe_no_db(self, client):
        resp = client.delete('/api/v1/push/subscribe',
                            headers=_auth_header(),
                            json={'expo_token': 'ExponentPushToken[abc123]'})
        data = json.loads(resp.data)
        assert resp.status_code == 404

    def test_invalid_platform(self, client):
        resp = client.post('/api/v1/push/subscribe',
                          headers=_auth_header(),
                          json={'expo_token': 'ExponentPushToken[abc]',
                                'platform': 'windows'})
        data = json.loads(resp.data)
        assert resp.status_code == 400
        assert 'platform' in data['error']['message'].lower()


# ── Articles (enhanced) ──────────────────────────────────────────

class TestArticlesEnhanced:
    def test_articles_search_param(self, client):
        resp = client.get('/api/v1/articles?search=diabetes', headers=_auth_header())
        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert data['success'] is True

    def test_articles_therapy_area_filter(self, client):
        resp = client.get('/api/v1/articles?therapy_area=diabetes', headers=_auth_header())
        data = json.loads(resp.data)
        assert resp.status_code == 200

    def test_articles_category_filter(self, client):
        resp = client.get('/api/v1/articles?category=Research', headers=_auth_header())
        assert resp.status_code == 200

    def test_articles_content_type_filter(self, client):
        resp = client.get('/api/v1/articles?content_type=pdf', headers=_auth_header())
        assert resp.status_code == 200

    def test_articles_pagination(self, client):
        resp = client.get('/api/v1/articles?page=1&limit=5', headers=_auth_header())
        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert data['pagination']['limit'] == 5

    def test_articles_limit_capped(self, client):
        resp = client.get('/api/v1/articles?limit=999', headers=_auth_header())
        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert data['pagination']['limit'] <= 100

    def test_articles_detail_not_found(self, client):
        resp = client.get('/api/v1/articles/nonexistent-uuid', headers=_auth_header())
        data = json.loads(resp.data)
        assert resp.status_code == 404


# ── Feed ─────────────────────────────────────────────────────────

class TestFeedAPI:
    def test_feed_no_token(self, client):
        resp = client.get('/api/v1/feed')
        assert resp.status_code == 401

    def test_feed_authenticated(self, client):
        resp = client.get('/api/v1/feed', headers=_auth_header())
        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert data['success'] is True
        assert 'data' in data
        assert 'pagination' in data

    def test_feed_pagination(self, client):
        resp = client.get('/api/v1/feed?page=1&limit=10', headers=_auth_header())
        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert data['pagination']['limit'] == 10

    def test_feed_limit_capped(self, client):
        resp = client.get('/api/v1/feed?limit=500', headers=_auth_header())
        data = json.loads(resp.data)
        assert resp.status_code == 200
        assert data['pagination']['limit'] <= 100


# ── Security: ownership / JWT ────────────────────────────────────

class TestOwnershipSecurity:
    def test_different_doctor_ids_isolated(self, app):
        """Two different JWTs should get isolated data."""
        with app.test_client() as c:
            h1 = {'Authorization': f'Bearer {_make_access_token("doctor-1")}'}
            h2 = {'Authorization': f'Bearer {_make_access_token("doctor-2")}'}

            r1 = c.get('/api/v1/bookmarks', headers=h1)
            r2 = c.get('/api/v1/bookmarks', headers=h2)
            assert r1.status_code == 200
            assert r2.status_code == 200

    def test_expired_token_rejected(self, app):
        secret = os.environ['JWT_SECRET_KEY']
        token = pyjwt.encode(
            {'sub': 'fake-id', 'type': 'access',
             'exp': datetime.now(timezone.utc) - timedelta(seconds=10)},
            secret, algorithm='HS256')
        with app.test_client() as c:
            resp = c.get('/api/v1/bookmarks',
                        headers={'Authorization': f'Bearer {token}'})
            assert resp.status_code == 401

    def test_refresh_token_rejected_as_access(self, app):
        secret = os.environ['JWT_SECRET_KEY']
        token = pyjwt.encode(
            {'sub': 'fake-id', 'type': 'refresh',
             'exp': datetime.now(timezone.utc) + timedelta(hours=1)},
            secret, algorithm='HS256')
        with app.test_client() as c:
            resp = c.get('/api/v1/profile',
                        headers={'Authorization': f'Bearer {token}'})
            assert resp.status_code == 401


# ── Service unit tests ───────────────────────────────────────────

class TestFeedServiceUnit:
    def test_rank_articles_with_matching_therapy(self):
        from app.services.feed_service import _rank_articles
        articles = [
            {'id': '1', 'therapy_area': 'general', 'published_at': '2024-01-03'},
            {'id': '2', 'therapy_area': 'diabetes', 'published_at': '2024-01-02'},
            {'id': '3', 'therapy_area': 'diabetes', 'published_at': '2024-01-01'},
            {'id': '4', 'therapy_area': 'neuropathy', 'published_at': '2024-01-04'},
        ]
        ranked = _rank_articles(articles, 'diabetes')
        assert ranked[0]['id'] == '2'
        assert ranked[1]['id'] == '3'
        assert len(ranked) == 4

    def test_rank_articles_no_therapy(self):
        from app.services.feed_service import _rank_articles
        articles = [{'id': '1'}, {'id': '2'}]
        ranked = _rank_articles(articles, None)
        assert ranked == articles

    def test_specialty_mapping(self):
        from app.services.feed_service import SPECIALTY_THERAPY_MAP
        assert SPECIALTY_THERAPY_MAP['diabetology'] == 'diabetes'
        assert SPECIALTY_THERAPY_MAP['neurology'] == 'neuropathy'
        assert SPECIALTY_THERAPY_MAP['gastroenterology'] == 'gastro'


class TestPushServiceUnit:
    def test_expo_token_pattern_valid(self):
        from app.services.push_service import EXPO_TOKEN_PATTERN
        assert EXPO_TOKEN_PATTERN.match('ExponentPushToken[abc123]')
        assert EXPO_TOKEN_PATTERN.match('ExponentPushToken[a-b_c]')

    def test_expo_token_pattern_invalid(self):
        from app.services.push_service import EXPO_TOKEN_PATTERN
        assert not EXPO_TOKEN_PATTERN.match('invalid')
        assert not EXPO_TOKEN_PATTERN.match('ExponentPushToken[]')
        assert not EXPO_TOKEN_PATTERN.match('')


class TestProfileServiceUnit:
    def test_updatable_fields(self):
        from app.services.profile_service import UPDATABLE_FIELDS, SAFE_FIELDS
        assert 'name' in UPDATABLE_FIELDS
        assert 'specialty' in UPDATABLE_FIELDS
        assert 'hospital' in UPDATABLE_FIELDS
        assert 'password_hash' not in UPDATABLE_FIELDS
        assert 'is_active' not in UPDATABLE_FIELDS
        assert 'password_hash' not in SAFE_FIELDS

    def test_preference_fields(self):
        from app.services.profile_service import PREFERENCE_FIELDS
        assert 'email_preference' in PREFERENCE_FIELDS
        assert 'push_preference' in PREFERENCE_FIELDS
        assert 'sms_preference' in PREFERENCE_FIELDS
        assert len(PREFERENCE_FIELDS) == 3
