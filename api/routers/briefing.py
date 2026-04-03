"""
Daily AI briefing endpoint — Layer 7A.

GET /api/briefing/daily  — latest AI-generated daily news digest
"""
import logging
from fastapi import APIRouter, HTTPException
from cachetools import TTLCache

from ..db import query
from ..models import DailyBriefing

router = APIRouter()
logger = logging.getLogger(__name__)

_cache: TTLCache = TTLCache(maxsize=1, ttl=600)   # 10-min cache


@router.get("/briefing/daily", response_model=DailyBriefing)
def get_daily_briefing():
    """Return the latest AI-generated daily news briefing."""
    if "briefing" in _cache:
        return _cache["briefing"]

    rows = query(
        """
        SELECT
            CAST(briefing_date AS STRING) AS briefing_date,
            briefing_text,
            article_count,
            top_entry_ids,
            generated_at
        FROM serve.daily_briefing
        ORDER BY generated_at DESC
        LIMIT 1
        """
    )

    if not rows:
        raise HTTPException(status_code=404, detail="No briefing available yet.")

    result = DailyBriefing(**rows[0])
    _cache["briefing"] = result
    return result
