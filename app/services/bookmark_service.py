"""Bookmark service — doctor article bookmarks."""

import logging
from app.extensions import sb

logger = logging.getLogger('tunes_pharma.bookmarks')


def get_bookmarks(doctor_id, page=1, limit=20):
    if not sb:
        return [], 0

    try:
        page = max(1, page)
        limit = max(1, min(limit, 100))
        offset = (page - 1) * limit

        count_result = (sb.table('bookmarks')
                        .select('id', count='exact')
                        .eq('doctor_id', doctor_id)
                        .execute())
        total = count_result.count if count_result.count is not None else len(count_result.data or [])

        result = (sb.table('bookmarks')
                  .select('id, paper_id, created_at')
                  .eq('doctor_id', doctor_id)
                  .order('created_at', desc=True)
                  .range(offset, offset + limit - 1)
                  .execute())
        bookmarks = result.data or []

        paper_ids = [b['paper_id'] for b in bookmarks]
        papers_map = {}
        if paper_ids:
            papers_result = (sb.table('papers')
                            .select('*')
                            .in_('id', paper_ids)
                            .eq('status', 'published')
                            .execute())
            papers_map = {p['id']: p for p in (papers_result.data or [])}

        enriched = []
        for b in bookmarks:
            paper = papers_map.get(b['paper_id'])
            enriched.append({
                'id': b['id'],
                'paper_id': b['paper_id'],
                'created_at': b['created_at'],
                'article': _serialize_article(paper) if paper else None,
            })

        return enriched, total
    except Exception as e:
        logger.error(f"get_bookmarks error: {e}")
        return [], 0


def create_bookmark(doctor_id, paper_id):
    if not sb:
        return None, 'Database unavailable.'

    try:
        paper = (sb.table('papers')
                 .select('id, status')
                 .eq('id', paper_id)
                 .execute())
        if not paper.data:
            return None, 'not_found'
        if paper.data[0].get('status') != 'published':
            return None, 'not_found'

        existing = (sb.table('bookmarks')
                    .select('id')
                    .eq('doctor_id', doctor_id)
                    .eq('paper_id', paper_id)
                    .execute())
        if existing.data:
            return existing.data[0], 'already_exists'

        result = (sb.table('bookmarks')
                  .insert({'doctor_id': doctor_id, 'paper_id': paper_id})
                  .execute())
        if result.data:
            return result.data[0], None
        return None, 'Insert failed.'
    except Exception as e:
        logger.error(f"create_bookmark error: {e}")
        return None, str(e)


def delete_bookmark(doctor_id, paper_id):
    if not sb:
        return False

    try:
        result = (sb.table('bookmarks')
                  .delete()
                  .eq('doctor_id', doctor_id)
                  .eq('paper_id', paper_id)
                  .execute())
        return bool(result.data)
    except Exception as e:
        logger.error(f"delete_bookmark error: {e}")
        return False


def _serialize_article(article):
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
    }
