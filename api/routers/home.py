"""
GET /api/home — Homepage sections

Returns:
  - top_stories: top 10 articles by importance_score
  - low_hype_picks: articles with hype_score < 0.3, sorted by importance
  - trending_topics: top trending topics
  - latest_briefs: 10 most recently published articles

Results are cached for cache_ttl_seconds (default 3 min).
"""
import time
import logging
from functools import lru_cache

from fastapi import APIRouter
from cachetools import TTLCache

from ..db import query
from ..config import settings
from ..models import HomeResponse, ArticleCard, TrendingTopic

router = APIRouter()
logger = logging.getLogger(__name__)

# Simple in-process TTL cache for homepage (single key)
_home_cache: TTLCache = TTLCache(maxsize=1, ttl=settings.cache_ttl_seconds)
_CACHE_KEY = "home"


def _fetch_home_data() -> HomeResponse:
    limit = settings.home_top_stories_limit

    top_stories_rows = query(
        f"""
        SELECT entry_id, title, source_name, published_at, category,
               summary_snippet, hype_score, credibility_score, importance_score,
               link, CAST(publish_date AS STRING) AS publish_date, image_url
        FROM serve.article_cards
        WHERE importance_score IS NOT NULL
        ORDER BY importance_score DESC
        LIMIT {limit}
        """
    )

    low_hype_rows = query(
        f"""
        SELECT entry_id, title, source_name, published_at, category,
               summary_snippet, hype_score, credibility_score, importance_score,
               link, CAST(publish_date AS STRING) AS publish_date, image_url
        FROM serve.article_cards
        WHERE hype_score IS NOT NULL AND hype_score < 0.3
          AND importance_score IS NOT NULL
        ORDER BY importance_score DESC
        LIMIT {limit}
        """
    )

    trending_rows = query(
        """
        SELECT topic, article_count, top_source, latest_at, category
        FROM serve.trending_topics
        ORDER BY article_count DESC
        LIMIT 10
        """
    )

    latest_rows = query(
        f"""
        SELECT entry_id, title, source_name, published_at, category,
               summary_snippet, hype_score, credibility_score, importance_score,
               link, CAST(publish_date AS STRING) AS publish_date, image_url
        FROM serve.article_cards
        ORDER BY published_at DESC
        LIMIT {limit}
        """
    )

    # Category rows: top 5 articles per top 4 categories (single query via ROW_NUMBER)
    cat_rows_raw = query(
        """
        SELECT entry_id, title, source_name, published_at, category,
               summary_snippet, hype_score, credibility_score, importance_score,
               link, CAST(publish_date AS STRING) AS publish_date, image_url, rn
        FROM (
          SELECT entry_id, title, source_name, published_at, category,
                 summary_snippet, hype_score, credibility_score, importance_score,
                 link, publish_date, image_url,
                 ROW_NUMBER() OVER (PARTITION BY category ORDER BY importance_score DESC NULLS LAST) AS rn
          FROM serve.article_cards
          WHERE category IS NOT NULL
            AND importance_score IS NOT NULL
            AND category IN (
              SELECT category FROM (
                SELECT category, COUNT(*) AS cnt
                FROM serve.article_cards
                WHERE category IS NOT NULL
                GROUP BY category ORDER BY cnt DESC LIMIT 4
              )
            )
        ) windowed
        WHERE rn <= 5
        ORDER BY category, rn
        """
    )

    category_rows: dict[str, list[ArticleCard]] = {}
    for r in cat_rows_raw:
        cat = r["category"]
        card_data = {k: v for k, v in r.items() if k != "rn"}
        category_rows.setdefault(cat, []).append(ArticleCard(**card_data))

    return HomeResponse(
        top_stories=[ArticleCard(**r) for r in top_stories_rows],
        low_hype_picks=[ArticleCard(**r) for r in low_hype_rows],
        trending_topics=[TrendingTopic(**r) for r in trending_rows],
        latest_briefs=[ArticleCard(**r) for r in latest_rows],
        category_rows=category_rows,
    )


@router.get("/home", response_model=HomeResponse)
def get_home():
    if _CACHE_KEY in _home_cache:
        return _home_cache[_CACHE_KEY]

    data = _fetch_home_data()
    _home_cache[_CACHE_KEY] = data
    return data
