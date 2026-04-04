"""
GET /api/topics/{topic}/history?days=N

Returns daily score snapshots for a topic so the frontend can show
hype/credibility trend evolution over time.
"""
import logging
from cachetools import TTLCache
from fastapi import APIRouter, Query as QParam

from ..config import settings
from ..db import query
from ..models import TopicHistoryPoint, TopicHistoryResponse

router = APIRouter()
logger = logging.getLogger(__name__)

_topics_cache: TTLCache = TTLCache(maxsize=128, ttl=settings.cache_ttl_seconds)


@router.get("/topics/{topic}/history", response_model=TopicHistoryResponse)
def get_topic_history(
    topic: str,
    days: int = QParam(default=30, ge=3, le=180),
):
    normalized = topic.strip()
    cache_key = f"{normalized.lower()}::{days}"
    if cache_key in _topics_cache:
        return _topics_cache[cache_key]

    rows = query(
        f"""
        SELECT
          CAST(snapshot_date AS STRING) AS snapshot_date,
          SUM(article_count) AS article_count,
          ROUND(AVG(avg_hype), 3) AS avg_hype,
          ROUND(AVG(avg_credibility), 3) AS avg_credibility,
          ROUND(AVG(avg_importance), 3) AS avg_importance
        FROM serve.hype_snapshots
        WHERE LOWER(topic) = LOWER(?)
          AND snapshot_date >= current_date - INTERVAL '{days}' DAY
        GROUP BY snapshot_date
        ORDER BY snapshot_date ASC
        """,
        (normalized,),
    )

    points = [TopicHistoryPoint(**dict(r)) for r in rows]
    # Quality gate for trend reliability:
    # treat points with fewer than 2 articles as low-confidence.
    qualified = [p for p in points if p.article_count >= 2]
    insufficient_data = len(qualified) < 2

    latest_hype = points[-1].avg_hype if points else None
    latest_credibility = points[-1].avg_credibility if points else None

    delta_hype_7d = None
    delta_credibility_7d = None
    if len(qualified) >= 2:
        start = qualified[max(0, len(qualified) - 7)]
        end = qualified[-1]
        if start.avg_hype is not None and end.avg_hype is not None:
            delta_hype_7d = round(end.avg_hype - start.avg_hype, 3)
        if start.avg_credibility is not None and end.avg_credibility is not None:
            delta_credibility_7d = round(end.avg_credibility - start.avg_credibility, 3)

    response = TopicHistoryResponse(
        topic=normalized,
        days=days,
        insufficient_data=insufficient_data,
        latest_hype=latest_hype,
        latest_credibility=latest_credibility,
        delta_hype_7d=delta_hype_7d,
        delta_credibility_7d=delta_credibility_7d,
        points=points,
    )
    _topics_cache[cache_key] = response
    return response
