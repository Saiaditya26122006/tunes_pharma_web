"""Doctor-facing notification service — read/mark notifications."""

import logging
from app.extensions import sb

logger = logging.getLogger('tunes_pharma.doctor_notifications')


def get_notifications(doctor_id, page=1, limit=20):
    if not sb:
        return [], 0

    try:
        page = max(1, page)
        limit = max(1, min(limit, 100))
        offset = (page - 1) * limit

        count_result = (sb.table('notifications')
                        .select('id', count='exact')
                        .eq('doctor_id', doctor_id)
                        .execute())
        total = count_result.count if count_result.count is not None else len(count_result.data or [])

        result = (sb.table('notifications')
                  .select('id, paper_id, is_read, created_at')
                  .eq('doctor_id', doctor_id)
                  .order('created_at', desc=True)
                  .range(offset, offset + limit - 1)
                  .execute())
        notifications = result.data or []

        paper_ids = list({n['paper_id'] for n in notifications if n.get('paper_id')})
        papers_map = {}
        if paper_ids:
            papers_result = (sb.table('papers')
                            .select('id, title, therapy_area, content_type, thumbnail_url, published_at')
                            .in_('id', paper_ids)
                            .execute())
            papers_map = {p['id']: p for p in (papers_result.data or [])}

        enriched = []
        for n in notifications:
            paper = papers_map.get(n.get('paper_id'))
            enriched.append({
                'id': n['id'],
                'paper_id': n.get('paper_id'),
                'is_read': n.get('is_read', False),
                'created_at': n.get('created_at'),
                'article': {
                    'id': paper['id'],
                    'title': paper.get('title', ''),
                    'therapy_area': paper.get('therapy_area', ''),
                    'content_type': paper.get('content_type', ''),
                    'thumbnail_url': paper.get('thumbnail_url'),
                    'published_at': paper.get('published_at'),
                } if paper else None,
            })

        return enriched, total
    except Exception as e:
        logger.error(f"get_notifications error: {e}")
        return [], 0


def mark_read(doctor_id, notification_id):
    if not sb:
        return False, 'Database unavailable.'

    try:
        check = (sb.table('notifications')
                 .select('id')
                 .eq('id', notification_id)
                 .eq('doctor_id', doctor_id)
                 .execute())
        if not check.data:
            return False, 'not_found'

        sb.table('notifications').update({'is_read': True}).eq('id', notification_id).execute()
        return True, None
    except Exception as e:
        logger.error(f"mark_read error: {e}")
        return False, str(e)


def mark_all_read(doctor_id):
    if not sb:
        return 0

    try:
        result = (sb.table('notifications')
                  .update({'is_read': True})
                  .eq('doctor_id', doctor_id)
                  .eq('is_read', False)
                  .execute())
        return len(result.data or [])
    except Exception as e:
        logger.error(f"mark_all_read error: {e}")
        return 0
