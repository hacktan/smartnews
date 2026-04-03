"""
GET /api/article/{id} — Full enriched article with AI fields

Queries serve.article_detail which contains all Gold + AI enrichment columns.
Not cached — individual articles are fast lookups by primary key.
"""
import logging
from fastapi import APIRouter, HTTPException
from cachetools import TTLCache

from ..db import query
from ..config import settings
from ..models import ArticleDetail, ArticleCard

router = APIRouter()
logger = logging.getLogger(__name__)

_article_cache: TTLCache = TTLCache(maxsize=200, ttl=settings.cache_ttl_seconds)


@router.get("/article/{entry_id}", response_model=ArticleDetail)
def get_article(entry_id: str):
    if entry_id in _article_cache:
        return _article_cache[entry_id]

    rows = query(
        """
        SELECT
            entry_id, title, dehyped_title, source_name, published_at, category, link,
            clean_summary, ai_summary, why_it_matters, hype_score, credibility_score,
            importance_score, freshness_score, entities, subtopic, language,
            word_count, read_time_min AS estimated_read_time_min,
            related_entry_ids, image_url
        FROM serve.article_detail
        WHERE entry_id = ?
        LIMIT 1
        """,
        (entry_id,),
    )

    if not rows:
        raise HTTPException(status_code=404, detail=f"Article '{entry_id}' not found.")

    row = dict(rows[0])
    related_ids_str: str = row.pop("related_entry_ids", "") or ""
    related_ids = [i.strip() for i in related_ids_str.split(",") if i.strip()][:5]

    related_articles: list[ArticleCard] = []
    if related_ids:
        placeholders = ",".join("?" * len(related_ids))
        related_rows = query(
            f"""
            SELECT entry_id, title, source_name, published_at, category,
                   summary_snippet, hype_score, credibility_score, importance_score,
                   link, CAST(publish_date AS STRING) AS publish_date, image_url
            FROM serve.article_cards
            WHERE entry_id IN ({placeholders})
            LIMIT 5
            """,
            tuple(related_ids),
        )
        related_articles = [ArticleCard(**r) for r in related_rows]

    result = ArticleDetail(**row, related_articles=related_articles)
    _article_cache[entry_id] = result
    return result
