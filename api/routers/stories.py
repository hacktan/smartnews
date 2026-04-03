"""
Compiled Stories endpoints — Layer 8 AI multi-source synthesis.

GET /api/stories           — list all compiled stories (newest first)
GET /api/story/{story_id}  — full detail: body, key claims, source articles
"""
import json
import logging
from fastapi import APIRouter, HTTPException
from cachetools import TTLCache

from ..db import query
from ..models import ArticleCard, CompiledStory, CompiledStoryDetail, CompiledStoriesResponse

router = APIRouter()
logger = logging.getLogger(__name__)

_list_cache: TTLCache = TTLCache(maxsize=1, ttl=300)
_detail_cache: TTLCache = TTLCache(maxsize=50, ttl=300)


@router.get("/stories", response_model=CompiledStoriesResponse)
def list_compiled_stories(limit: int = 20):
    """Return compiled multi-source stories, newest first."""
    cache_key = f"list_{limit}"
    if cache_key in _list_cache:
        return _list_cache[cache_key]

    rows = query(
        f"""
        SELECT
            story_id,
            compiled_title,
            compiled_summary,
            source_count,
            sources_used,
            category,
            first_published,
            last_published,
            compiled_at,
            entry_ids
        FROM serve.compiled_stories
        WHERE compiled_title IS NOT NULL
        ORDER BY last_published DESC
        LIMIT {min(limit, 50)}
        """
    )

    items = [CompiledStory(**r) for r in rows]
    result = CompiledStoriesResponse(items=items, total=len(items))
    _list_cache[cache_key] = result
    return result


@router.get("/story/{story_id}", response_model=CompiledStoryDetail)
def get_compiled_story(story_id: str):
    """Return full compiled story detail including body, claims, and source articles."""
    if story_id in _detail_cache:
        return _detail_cache[story_id]

    rows = query(
        """
        SELECT
            story_id,
            compiled_title,
            compiled_summary,
            compiled_body,
            source_count,
            sources_used,
            category,
            first_published,
            last_published,
            compiled_at,
            entry_ids,
            key_claims,
            consensus_points,
            divergence_points
        FROM serve.compiled_stories
        WHERE story_id = ?
        LIMIT 1
        """,
        params=(story_id,),
    )

    if not rows:
        raise HTTPException(status_code=404, detail="Compiled story not found.")

    row = rows[0]
    detail = CompiledStoryDetail(**row)

    # Fetch source article cards
    try:
        raw = row.get("entry_ids") or "[]"
        entry_ids = json.loads(raw) if raw.startswith("[") else raw.split(",")
        entry_ids = [e.strip() for e in entry_ids if e.strip()]
    except Exception:
        entry_ids = []

    if entry_ids:
        # Use safe string interpolation — entry_ids are MD5 hex strings (safe)
        id_list = ",".join(f"'{eid}'" for eid in entry_ids)
        card_rows = query(
            f"""
            SELECT
                entry_id,
                title,
                source_name,
                published_at,
                category,
                summary_snippet,
                hype_score,
                credibility_score,
                importance_score,
                link,
                CAST(publish_date AS STRING) AS publish_date,
                image_url
            FROM serve.article_cards
            WHERE entry_id IN ({id_list})
            ORDER BY published_at DESC
            """
        )
        detail.source_articles = [ArticleCard(**r) for r in card_rows]

    _detail_cache[story_id] = detail
    return detail
