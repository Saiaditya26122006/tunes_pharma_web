"""Feed service — deterministic rule-based article feed.

Ranking strategy (v1):
  1. Published articles only
  2. Articles matching the doctor's specialty therapy area get a boost
  3. Recent articles ranked higher
  4. Fallback: all published articles sorted by published_at desc

Designed so a future ML recommendation system can replace get_feed()
without changing the API layer.
"""

import logging
from app.extensions import sb

logger = logging.getLogger('tunes_pharma.feed')

SPECIALTY_THERAPY_MAP = {
    'diabetology': 'diabetes',
    'diabetologist': 'diabetes',
    'endocrinology': 'diabetes',
    'endocrinologist': 'diabetes',
    'neurology': 'neuropathy',
    'neurologist': 'neuropathy',
    'gastroenterology': 'gastro',
    'gastroenterologist': 'gastro',
}


def get_feed(doctor_id, page=1, limit=20):
    if not sb:
        return [], 0

    try:
        page = max(1, page)
        limit = max(1, min(limit, 100))

        doctor_therapy = _get_doctor_therapy_area(doctor_id)

        count_result = (sb.table('papers')
                        .select('id', count='exact')
                        .eq('status', 'published')
                        .execute())
        total = count_result.count if count_result.count is not None else len(count_result.data or [])

        all_result = (sb.table('papers')
                      .select('*')
                      .eq('status', 'published')
                      .order('published_at', desc=True)
                      .execute())
        articles = all_result.data or []

        ranked = _rank_articles(articles, doctor_therapy)

        offset = (page - 1) * limit
        page_items = ranked[offset:offset + limit]

        return [_serialize(a) for a in page_items], total
    except Exception as e:
        logger.error(f"get_feed error: {e}")
        return [], 0


def _get_doctor_therapy_area(doctor_id):
    try:
        result = (sb.table('doctors')
                  .select('specialty')
                  .eq('id', doctor_id)
                  .execute())
        if not result.data:
            return None
        specialty = (result.data[0].get('specialty') or '').lower().strip()
        return SPECIALTY_THERAPY_MAP.get(specialty)
    except Exception:
        return None


def _rank_articles(articles, doctor_therapy):
    if not doctor_therapy:
        return articles

    matched = []
    rest = []
    for a in articles:
        if a.get('therapy_area') == doctor_therapy:
            matched.append(a)
        else:
            rest.append(a)
    return matched + rest


def _serialize(article):
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
