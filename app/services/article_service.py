"""Article/paper service — abstracts Supabase queries for the papers table."""

import logging
from app.extensions import sb

logger = logging.getLogger('tunes_pharma.articles')


def get_published_articles(page=1, limit=20, therapy_area=None, category=None,
                           content_type=None, search=None):
    """Return published articles with pagination.

    Returns (articles_list, total_count).
    """
    if not sb:
        return [], 0

    try:
        # Count query
        count_q = sb.table('papers').select('id', count='exact').eq('status', 'published')
        if therapy_area and therapy_area != 'all':
            count_q = count_q.eq('therapy_area', therapy_area)
        if category:
            count_q = count_q.eq('category', category)
        if content_type:
            count_q = count_q.eq('content_type', content_type)
        if search:
            count_q = count_q.or_(f"title.ilike.%{search}%,description.ilike.%{search}%")
        count_result = count_q.execute()
        total = count_result.count if count_result.count is not None else len(count_result.data or [])

        # Data query
        page = max(1, page)
        limit = max(1, min(limit, 100))
        offset = (page - 1) * limit

        data_q = (sb.table('papers')
                  .select('*')
                  .eq('status', 'published')
                  .order('published_at', desc=True))
        if therapy_area and therapy_area != 'all':
            data_q = data_q.eq('therapy_area', therapy_area)
        if category:
            data_q = data_q.eq('category', category)
        if content_type:
            data_q = data_q.eq('content_type', content_type)
        if search:
            data_q = data_q.or_(f"title.ilike.%{search}%,description.ilike.%{search}%")

        data_q = data_q.range(offset, offset + limit - 1)
        result = data_q.execute()
        articles = result.data or []

        return articles, total
    except Exception as e:
        logger.error(f"get_published_articles error: {e}")
        return [], 0


def get_article_by_id(article_id, published_only=True):
    """Return a single article by ID, or None."""
    if not sb:
        return None
    try:
        q = sb.table('papers').select('*').eq('id', article_id)
        if published_only:
            q = q.eq('status', 'published')
        result = q.execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"get_article_by_id error: {e}")
        return None


def serialize_article(article):
    """Convert a paper record to a clean API-safe dict."""
    if not article:
        return None
    return {
        'id': article['id'],
        'title': article.get('title', ''),
        'description': article.get('description', ''),
        'content_type': article.get('content_type', ''),
        'file_url': article.get('file_url', ''),
        'therapy_area': article.get('therapy_area', ''),
        'author': article.get('author', ''),
        'category': article.get('category', ''),
        'thumbnail_url': article.get('thumbnail_url'),
        'published_at': article.get('published_at'),
        'created_at': article.get('created_at'),
    }
