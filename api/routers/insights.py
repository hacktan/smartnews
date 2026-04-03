"""
Media literacy insights endpoints — Layer 6C.

GET /api/insights/blind-spots   — entities/articles covered by only one source
"""
import logging
from fastapi import APIRouter
from cachetools import TTLCache

from ..db import query
from ..models import BlindSpotItem, BlindSpotsResponse

router = APIRouter()
logger = logging.getLogger(__name__)

_cache: TTLCache = TTLCache(maxsize=1, ttl=300)


@router.get("/insights/blind-spots", response_model=BlindSpotsResponse)
def get_blind_spots(limit: int = 12):
    """
    Return important entities that are mentioned in articles from only one
    distinct source in the last 7 days — these are stories flying under the
    mainstream radar.
    """
    if "blind_spots" in _cache:
        return _cache["blind_spots"]

    rows = query(
        f"""
        SELECT
            ei.entity_name,
            ei.entity_type,
            ei.entry_id,
            ei.title,
            ei.source_name,
            ei.category,
            ei.published_at,
            ei.importance_score,
            ei.hype_score,
            ei.credibility_score
        FROM serve.entity_index ei
        INNER JOIN (
            SELECT entity_name
            FROM serve.entity_index
            WHERE published_at >= current_timestamp() - INTERVAL 7 DAYS
              AND entity_type IN ('PERSON', 'ORG', 'PLACE', 'EVENT')
            GROUP BY entity_name
            HAVING COUNT(DISTINCT source_name) = 1
               AND COUNT(*) >= 1
        ) single_source USING (entity_name)
        WHERE ei.published_at >= current_timestamp() - INTERVAL 7 DAYS
          AND ei.importance_score IS NOT NULL
          AND ei.importance_score > 0.45
        ORDER BY ei.importance_score DESC, ei.published_at DESC
        LIMIT {limit}
        """
    )

    result = BlindSpotsResponse(items=[BlindSpotItem(**r) for r in rows])
    _cache["blind_spots"] = result
    return result
