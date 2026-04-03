"""
Entity-centric navigation endpoints.

GET /api/entities              — top entities by article count (last 30 days)
GET /api/entity/{name}         — all articles mentioning entity + aggregate scores
"""
import logging
from urllib.parse import unquote
from fastapi import APIRouter, HTTPException
from cachetools import TTLCache

from ..db import query
from ..models import EntityResponse, EntityArticle, TopEntitiesResponse, EntitySummary

router = APIRouter()
logger = logging.getLogger(__name__)

_top_cache: TTLCache = TTLCache(maxsize=1, ttl=300)
_entity_cache: TTLCache = TTLCache(maxsize=200, ttl=120)


@router.get("/entities", response_model=TopEntitiesResponse)
def get_top_entities(limit: int = 30):
    """Return top entities by mention count across all recent articles."""
    cache_key = f"top_{limit}"
    if cache_key in _top_cache:
        return _top_cache[cache_key]

    rows = query(
        f"""
        SELECT
            entity_name,
            entity_type,
            COUNT(*) AS article_count,
            ROUND(AVG(credibility_score), 3) AS avg_credibility,
            ROUND(AVG(hype_score), 3) AS avg_hype
        FROM serve.entity_index
        GROUP BY entity_name, entity_type
        ORDER BY article_count DESC
        LIMIT {limit}
        """
    )

    result = TopEntitiesResponse(
        entities=[EntitySummary(**r) for r in rows]
    )
    _top_cache[cache_key] = result
    return result


@router.get("/entity/{entity_name}", response_model=EntityResponse)
def get_entity(entity_name: str):
    """Return all articles mentioning an entity, with aggregate score context."""
    name = unquote(entity_name).strip()
    if not name:
        raise HTTPException(status_code=400, detail="entity_name is required")

    cache_key = name.lower()
    if cache_key in _entity_cache:
        return _entity_cache[cache_key]

    # Aggregate stats
    agg_rows = query(
        """
        SELECT
            entity_name,
            entity_type,
            COUNT(*) AS article_count,
            ROUND(AVG(hype_score), 3) AS avg_hype,
            ROUND(AVG(credibility_score), 3) AS avg_credibility,
            ROUND(AVG(importance_score), 3) AS avg_importance
        FROM serve.entity_index
        WHERE LOWER(entity_name) = LOWER(?)
        GROUP BY entity_name, entity_type
        LIMIT 1
        """,
        (name,),
    )

    if not agg_rows:
        raise HTTPException(status_code=404, detail=f"Entity '{name}' not found.")

    agg = dict(agg_rows[0])

    # Articles for this entity, most recent first
    article_rows = query(
        """
        SELECT
            entry_id, title, source_name, category, published_at,
            hype_score, credibility_score, importance_score
        FROM serve.entity_index
        WHERE LOWER(entity_name) = LOWER(?)
        ORDER BY published_at DESC
        LIMIT 50
        """,
        (name,),
    )

    result = EntityResponse(
        entity_name=agg["entity_name"],
        entity_type=agg.get("entity_type"),
        article_count=agg["article_count"],
        avg_hype=agg.get("avg_hype"),
        avg_credibility=agg.get("avg_credibility"),
        avg_importance=agg.get("avg_importance"),
        articles=[EntityArticle(**r) for r in article_rows],
    )
    _entity_cache[cache_key] = result
    return result
