"""API v1 blueprint — JWT-authenticated endpoints for mobile/external clients."""

from flask import Blueprint, request, g

from app.middleware.auth import doctor_required
from app.services.auth_service import (
    authenticate_doctor, create_token_pair,
    refresh_access_token, revoke_refresh_token,
    check_rate_limit,
)
from app.services.article_service import (
    get_published_articles, get_article_by_id, serialize_article,
)
from app.services import bookmark_service, profile_service, doctor_notification_service
from app.services import push_service, feed_service
from app.utils.responses import success_response, error_response, build_pagination
from app.extensions import sb

api_v1_bp = Blueprint('api_v1', __name__)


# ── Auth endpoints ────────────────────────────────────────────────

@api_v1_bp.route('/auth/login', methods=['POST'])
def auth_login():
    data = request.get_json(silent=True)
    if not data:
        return error_response('BAD_REQUEST', 'JSON body required.', 400)

    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return error_response('BAD_REQUEST', 'Username and password are required.', 400)

    ip = request.remote_addr or 'unknown'
    if not check_rate_limit(ip, 'doctor_login', max_attempts=5, window_seconds=300):
        return error_response('RATE_LIMITED', 'Too many login attempts. Try again later.', 429)

    doctor = authenticate_doctor(username, password)
    if not doctor:
        return error_response('UNAUTHORIZED', 'Invalid credentials.', 401)

    tokens = create_token_pair(doctor)
    return success_response({
        'tokens': tokens,
        'doctor': {
            'id': doctor['id'],
            'name': doctor.get('name', ''),
            'specialty': doctor.get('specialty', ''),
        },
    })


@api_v1_bp.route('/auth/refresh', methods=['POST'])
def auth_refresh():
    data = request.get_json(silent=True)
    if not data or not data.get('refresh_token'):
        return error_response('BAD_REQUEST', 'refresh_token is required.', 400)

    tokens, err = refresh_access_token(data['refresh_token'])
    if err:
        return error_response('UNAUTHORIZED', err, 401)

    return success_response({'tokens': tokens})


@api_v1_bp.route('/auth/logout', methods=['POST'])
@doctor_required
def auth_logout():
    data = request.get_json(silent=True)
    if data and data.get('refresh_token'):
        revoke_refresh_token(data['refresh_token'])
    return success_response({'message': 'Logged out.'})


@api_v1_bp.route('/auth/me', methods=['GET'])
@doctor_required
def auth_me():
    if not sb:
        return error_response('SERVICE_UNAVAILABLE', 'Database unavailable.', 503)

    try:
        result = sb.table('doctors').select('*').eq('id', g.doctor_id).execute()
        if not result.data:
            return error_response('NOT_FOUND', 'Doctor not found.', 404)
        doc = result.data[0]
        return success_response({
            'id': doc['id'],
            'name': doc.get('name', ''),
            'specialty': doc.get('specialty', ''),
            'hospital': doc.get('hospital', ''),
            'email': doc.get('email', ''),
            'phone': doc.get('phone', ''),
            'username': doc.get('username', ''),
        })
    except Exception:
        return error_response('INTERNAL_ERROR', 'Failed to fetch profile.', 500)


# ── Articles endpoints (published only) ──────────────────────────

@api_v1_bp.route('/articles', methods=['GET'])
@doctor_required
def articles_list():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    therapy_area = request.args.get('therapy_area')
    category = request.args.get('category')
    content_type = request.args.get('content_type')
    search = request.args.get('search')

    articles, total = get_published_articles(
        page=page, limit=limit,
        therapy_area=therapy_area, category=category,
        content_type=content_type, search=search,
    )

    return success_response(
        data=[serialize_article(a) for a in articles],
        pagination=build_pagination(page, min(max(1, limit), 100), total),
    )


@api_v1_bp.route('/articles/<article_id>', methods=['GET'])
@doctor_required
def articles_detail(article_id):
    article = get_article_by_id(article_id, published_only=True)
    if not article:
        return error_response('NOT_FOUND', 'Article not found.', 404)

    return success_response(data=serialize_article(article))


# ── Bookmarks ────────────────────────────────────────────────────

@api_v1_bp.route('/bookmarks', methods=['GET'])
@doctor_required
def bookmarks_list():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    limit = max(1, min(limit, 100))

    bookmarks, total = bookmark_service.get_bookmarks(g.doctor_id, page, limit)
    return success_response(
        data=bookmarks,
        pagination=build_pagination(page, limit, total),
    )


@api_v1_bp.route('/bookmarks/<article_id>', methods=['POST'])
@doctor_required
def bookmarks_create(article_id):
    bookmark, err = bookmark_service.create_bookmark(g.doctor_id, article_id)
    if err == 'not_found':
        return error_response('NOT_FOUND', 'Article not found or not published.', 404)
    if err == 'already_exists':
        return success_response(data={'id': bookmark['id'], 'article_id': article_id}, status=200)
    if err:
        return error_response('INTERNAL_ERROR', 'Failed to create bookmark.', 500)
    return success_response(data={'id': bookmark['id'], 'article_id': article_id}, status=201)


@api_v1_bp.route('/bookmarks/<article_id>', methods=['DELETE'])
@doctor_required
def bookmarks_delete(article_id):
    deleted = bookmark_service.delete_bookmark(g.doctor_id, article_id)
    if not deleted:
        return error_response('NOT_FOUND', 'Bookmark not found.', 404)
    return success_response(data={'message': 'Bookmark removed.'})


# ── Profile ──────────────────────────────────────────────────────

@api_v1_bp.route('/profile', methods=['GET'])
@doctor_required
def profile_get():
    profile = profile_service.get_profile(g.doctor_id)
    if not profile:
        return error_response('NOT_FOUND', 'Profile not found.', 404)
    return success_response(data=profile)


@api_v1_bp.route('/profile', methods=['PATCH'])
@doctor_required
def profile_update():
    data = request.get_json(silent=True)
    if not data:
        return error_response('BAD_REQUEST', 'JSON body required.', 400)

    profile, err = profile_service.update_profile(g.doctor_id, data)
    if err:
        return error_response('BAD_REQUEST', err, 400)
    return success_response(data=profile)


# ── Notification preferences ─────────────────────────────────────

@api_v1_bp.route('/profile/notifications', methods=['GET'])
@doctor_required
def notification_prefs_get():
    prefs = profile_service.get_notification_preferences(g.doctor_id)
    if prefs is None:
        return error_response('NOT_FOUND', 'Profile not found.', 404)
    return success_response(data=prefs)


@api_v1_bp.route('/profile/notifications', methods=['PATCH'])
@doctor_required
def notification_prefs_update():
    data = request.get_json(silent=True)
    if not data:
        return error_response('BAD_REQUEST', 'JSON body required.', 400)

    prefs, err = profile_service.update_notification_preferences(g.doctor_id, data)
    if err:
        return error_response('BAD_REQUEST', err, 400)
    return success_response(data=prefs)


# ── Notifications ────────────────────────────────────────────────

@api_v1_bp.route('/notifications', methods=['GET'])
@doctor_required
def notifications_list():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    limit = max(1, min(limit, 100))

    notifications, total = doctor_notification_service.get_notifications(g.doctor_id, page, limit)
    return success_response(
        data=notifications,
        pagination=build_pagination(page, limit, total),
    )


@api_v1_bp.route('/notifications/<notification_id>/read', methods=['PATCH'])
@doctor_required
def notifications_mark_read(notification_id):
    ok, err = doctor_notification_service.mark_read(g.doctor_id, notification_id)
    if err == 'not_found':
        return error_response('NOT_FOUND', 'Notification not found.', 404)
    if not ok:
        return error_response('INTERNAL_ERROR', 'Failed to mark as read.', 500)
    return success_response(data={'message': 'Marked as read.'})


@api_v1_bp.route('/notifications/read-all', methods=['POST'])
@doctor_required
def notifications_mark_all_read():
    count = doctor_notification_service.mark_all_read(g.doctor_id)
    return success_response(data={'marked': count})


# ── Push token registration ──────────────────────────────────────

@api_v1_bp.route('/push/subscribe', methods=['POST'])
@doctor_required
def push_subscribe():
    data = request.get_json(silent=True)
    if not data or not data.get('expo_token'):
        return error_response('BAD_REQUEST', 'expo_token is required.', 400)

    result, err = push_service.subscribe(
        g.doctor_id,
        data['expo_token'],
        platform=data.get('platform'),
    )
    if err == 'already_exists':
        return success_response(data={'message': 'Token already registered.'}, status=200)
    if err:
        return error_response('BAD_REQUEST', err, 400)
    return success_response(data={'message': 'Push token registered.'}, status=201)


@api_v1_bp.route('/push/subscribe', methods=['DELETE'])
@doctor_required
def push_unsubscribe():
    data = request.get_json(silent=True)
    if not data or not data.get('expo_token'):
        return error_response('BAD_REQUEST', 'expo_token is required.', 400)

    deleted = push_service.unsubscribe(g.doctor_id, data['expo_token'])
    if not deleted:
        return error_response('NOT_FOUND', 'Token not found.', 404)
    return success_response(data={'message': 'Token removed.'})


# ── Feed ─────────────────────────────────────────────────────────

@api_v1_bp.route('/feed', methods=['GET'])
@doctor_required
def feed():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    limit = max(1, min(limit, 100))

    articles, total = feed_service.get_feed(g.doctor_id, page, limit)
    return success_response(
        data=articles,
        pagination=build_pagination(page, limit, total),
    )
