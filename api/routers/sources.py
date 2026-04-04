"""
GET /api/sources/leaderboard

Aggregates stats per source from serve.article_cards.
"""
import logging
from fastapi import APIRouter
from typing import List

from ..db import query
from ..models import SourceLeaderboardItem, SourceLeaderboardResponse

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/sources/leaderboard", response_model=SourceLeaderboardResponse)
def get_source_leaderboard():
    """
    Returns a leaderboard of news sources, ranked by average credibility.
    The stats are aggregated from all articles in the `serve.article_cards` table.
    """
    sql = """
        SELECT
            source_name,
            COUNT(*) AS article_count,
            ROUND(AVG(credibility_score), 3) AS avg_credibility,
            ROUND(AVG(hype_score), 3) AS avg_hype,
            ROUND(AVG(importance_score), 3) AS avg_importance
        FROM serve.article_cards
        WHERE source_name IS NOT NULL
          AND credibility_score IS NOT NULL
          AND credibility_score != 0.5
        GROUP BY source_name
        HAVING COUNT(*) > 1
        ORDER BY avg_credibility DESC, article_count DESC
        LIMIT 50
    """
    rows = query(sql, ())
    
    return SourceLeaderboardResponse(
        sources=[SourceLeaderboardItem(**r) for r in rows]
    )
