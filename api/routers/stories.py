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


def _is_pending_placeholder(summary: str | None, body: str | None) -> bool:
    s = (summary or "").strip().lower()
    b = (body or "").strip().lower()
    return (
        s.startswith("ai synthesis pending")
        or s.startswith("ai full synthesis is pending")
        or b.startswith("this story has been matched across multiple sources")
    )


@router.get("/stories", response_model=CompiledStoriesResponse)
def list_compiled_stories(limit: int = 20, include_pending: bool = False):
    """Return compiled multi-source stories, newest first."""
    cache_key = f"list_{limit}:{include_pending}"
    if cache_key in _list_cache:
        return _list_cache[cache_key]

    safe_limit = max(1, min(limit, 50))

    body_filter = "" if include_pending else "AND COALESCE(LENGTH(compiled_body), 0) >= 300"
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
          {body_filter}
        ORDER BY last_published DESC
        LIMIT {safe_limit}
        """
    )

    items = [
        CompiledStory(**r)
        for r in rows
        if include_pending or not _is_pending_placeholder(r.get("compiled_summary"), None)
    ]

    # Optional fallback: expose pending multi-source matches only when explicitly requested.
    if include_pending and len(items) < safe_limit:
        fallback_rows = query(
            f"""
            SELECT
                sm.story_id,
                sm.canonical_title,
                sm.source_count,
                sm.sources,
                sm.category,
                sm.first_published,
                sm.last_published,
                sm.entry_ids,
                sm.matched_at
            FROM gold.story_matches sm
            LEFT JOIN serve.compiled_stories cs ON cs.story_id = sm.story_id
            WHERE cs.story_id IS NULL
              AND sm.source_count >= 2
            ORDER BY sm.last_published DESC
            LIMIT {safe_limit - len(items)}
            """
        )

        for r in fallback_rows:
            items.append(
                CompiledStory(
                    story_id=r["story_id"],
                    compiled_title=r.get("canonical_title") or "Emerging multi-source story",
                    compiled_summary="AI full synthesis is pending; open to compare source coverage now.",
                    source_count=r.get("source_count"),
                    sources_used=r.get("sources"),
                    category=r.get("category"),
                    first_published=r.get("first_published"),
                    last_published=r.get("last_published"),
                    compiled_at=r.get("matched_at"),
                    entry_ids=r.get("entry_ids"),
                )
            )

    result = CompiledStoriesResponse(items=items, total=len(items))
    _list_cache[cache_key] = result
    return result


@router.get("/story/{story_id}", response_model=CompiledStoryDetail)
def get_compiled_story(story_id: str, include_pending: bool = False):
    """Return full compiled story detail including body, claims, and source articles."""
    cache_key = f"{story_id}:{include_pending}"
    if cache_key in _detail_cache:
        return _detail_cache[cache_key]

    detail_body_filter = "" if include_pending else "AND COALESCE(LENGTH(compiled_body), 0) >= 300"

    rows = query(
        f"""
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
                    {detail_body_filter}
        LIMIT 1
                """,
        params=(story_id,),
    )

    if not rows and not include_pending:
        raise HTTPException(status_code=404, detail="Compiled story not found.")

    if not rows:
        fallback = query(
            """
            SELECT
                story_id,
                canonical_title,
                source_count,
                sources,
                category,
                first_published,
                last_published,
                entry_ids,
                matched_at
            FROM gold.story_matches
            WHERE story_id = ?
              AND source_count >= 2
            LIMIT 1
            """,
            params=(story_id,),
        )

        if not fallback:
            raise HTTPException(status_code=404, detail="Compiled story not found.")

        f = fallback[0]
        detail = CompiledStoryDetail(
            story_id=f["story_id"],
            compiled_title=f.get("canonical_title") or "Emerging multi-source story",
            compiled_summary="AI full synthesis is pending; this view lists source coverage and key article snippets.",
            compiled_body="",
            source_count=f.get("source_count"),
            sources_used=f.get("sources"),
            category=f.get("category"),
            first_published=f.get("first_published"),
            last_published=f.get("last_published"),
            compiled_at=f.get("matched_at"),
            entry_ids=f.get("entry_ids"),
            key_claims="[]",
            consensus_points="[]",
            divergence_points="[]",
            source_articles=[],
        )

        try:
            raw = f.get("entry_ids") or "[]"
            entry_ids = json.loads(raw) if raw.startswith("[") else raw.split(",")
            entry_ids = [e.strip() for e in entry_ids if e.strip()]
        except Exception:
            entry_ids = []

        if entry_ids:
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

            snippets = []
            for c in card_rows[:6]:
                title = c.get("title") or "Untitled"
                source = c.get("source_name") or "Unknown source"
                summary = (c.get("summary_snippet") or "").strip()
                if summary:
                    snippets.append(f"- {title} ({source}): {summary}")
                else:
                    snippets.append(f"- {title} ({source})")

            detail.compiled_body = (
                "This story has been matched across multiple sources, but full AI synthesis is not available yet.\n\n"
                + "\n".join(snippets)
            )

        _detail_cache[cache_key] = detail
        return detail

    row = rows[0]
    if not include_pending and _is_pending_placeholder(row.get("compiled_summary"), row.get("compiled_body")):
        raise HTTPException(status_code=404, detail="Compiled story not found.")

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

    _detail_cache[cache_key] = detail
    return detail
