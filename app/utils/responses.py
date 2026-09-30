"""Consistent JSON response helpers for the API layer."""

from flask import jsonify


def success_response(data=None, status=200, pagination=None):
    body = {'success': True}
    if data is not None:
        body['data'] = data
    if pagination is not None:
        body['pagination'] = pagination
    return jsonify(body), status


def error_response(code, message, status=400, details=None):
    body = {
        'success': False,
        'error': {
            'code': code,
            'message': message,
        }
    }
    if details is not None:
        body['error']['details'] = details
    return jsonify(body), status


def paginate_query(query, page=1, limit=20):
    """Apply offset/limit pagination to a Supabase query builder.

    Returns (query_with_range, offset) so the caller can execute and then
    build the pagination metadata via ``build_pagination()``.
    """
    page = max(1, page)
    limit = max(1, min(limit, 100))
    offset = (page - 1) * limit
    return query.range(offset, offset + limit - 1), page, limit


def build_pagination(page, limit, total):
    return {
        'page': page,
        'limit': limit,
        'total': total,
        'has_next': (page * limit) < total,
    }
