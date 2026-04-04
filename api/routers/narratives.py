"""
Narrative Tracker endpoints — Layer 7B.

GET /api/narratives                — list active narrative arcs (multi-article subtopics)
GET /api/narratives/{arc_id}       — full narrative detail with timeline articles
"""
import json
import logging
from fastapi import APIRouter, HTTPException
from cachetools import TTLCache

from ..db import query
from ..models import ArticleCard, NarrativeArc, NarrativeDetail, NarrativesResponse

router = APIRouter()
logger = logging.getLogger(__name__)

_list_cache: TTLCache = TTLCache(maxsize=1, ttl=300)
_detail_cache: TTLCache = TTLCache(maxsize=64, ttl=300)


@router.get("/narratives", response_model=NarrativesResponse)
def list_narratives(limit: int = 20, category: str = ""):
    """
    Return narrative arcs — groups of 2+ articles about the same evolving story,
    ordered by importance descending. Each arc exposes hype_trend to signal
    whether the story is escalating or cooling down.
    """
    cache_key = f"{limit}:{category}"
    if cache_key in _list_cache:
        return _list_cache[cache_key]

    cat_filter = f"AND category = '{category}'" if category else ""

    safe_limit = max(1, min(limit, 100))

    rows = query(
        f"""
        SELECT
            arc_id,
            subtopic,
            category,
            article_count,
            first_seen,
            last_seen,
            span_days,
            hype_start,
            hype_end,
            hype_trend,
            avg_importance,
            avg_hype,
            avg_credibility,
            latest_title
        FROM serve.story_arcs
        WHERE 1=1 {cat_filter}
        ORDER BY avg_importance DESC, article_count DESC
        LIMIT {safe_limit}
        """
    )

    items = [NarrativeArc(**r) for r in rows]

    # Fallback: if there are too few explicit arcs, synthesize narrative cards from story clusters.
    if len(items) < safe_limit:
        remaining = safe_limit - len(items)
        cluster_rows = query(
            f"""
            SELECT
                cluster_id,
                label,
                article_count,
                top_categories,
                avg_importance,
                avg_hype,
                avg_credibility
            FROM serve.story_clusters
            WHERE article_count >= 2
            ORDER BY avg_importance DESC, article_count DESC
            LIMIT {remaining * 2}
            """
        )

        existing_ids = {arc.arc_id for arc in items}
        for r in cluster_rows:
            cid = int(r["cluster_id"])
            arc_id = f"cluster-{cid}"
            if arc_id in existing_ids:
                continue

            title = r.get("label") or f"Cluster {cid + 1}"
            category_name = r.get("top_categories") or "General"
            items.append(
                NarrativeArc(
                    arc_id=arc_id,
                    subtopic=title,
                    category=category_name,
                    article_count=int(r.get("article_count") or 0),
                    first_seen=None,
                    last_seen=None,
                    span_days=None,
                    hype_start=r.get("avg_hype"),
                    hype_end=r.get("avg_hype"),
                    hype_trend=0.0,
                    avg_importance=r.get("avg_importance"),
                    avg_hype=r.get("avg_hype"),
                    avg_credibility=r.get("avg_credibility"),
                    latest_title=None,
                )
            )
            existing_ids.add(arc_id)

            if len(items) >= safe_limit:
                break

    items = items[:safe_limit]
    result = NarrativesResponse(items=items, total=len(items))
    _list_cache[cache_key] = result
    return result


@router.get("/narratives/{arc_id}", response_model=NarrativeDetail)
def get_narrative(arc_id: str):
    """
    Return a single narrative arc with its full ordered timeline of articles.
    """
    if arc_id in _detail_cache:
        return _detail_cache[arc_id]

    if arc_id.startswith("cluster-"):
        try:
            cluster_id = int(arc_id.split("-", 1)[1])
        except Exception:
            raise HTTPException(status_code=404, detail="Narrative arc not found")

        c_rows = query(
            """
            SELECT
                cluster_id,
                label,
                article_count,
                top_categories,
                avg_importance,
                avg_hype,
                avg_credibility
            FROM serve.story_clusters
            WHERE cluster_id = ?
            LIMIT 1
            """,
            params=(cluster_id,),
        )

        if not c_rows:
            raise HTTPException(status_code=404, detail="Narrative arc not found")

        cluster = c_rows[0]
        article_rows = query(
            """
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
            WHERE cluster_id = ?
            ORDER BY importance_score DESC NULLS LAST, published_at DESC
            LIMIT 20
            """,
            params=(cluster_id,),
        )
        articles = [ArticleCard(**r) for r in article_rows]

        detail = NarrativeDetail(
            arc_id=arc_id,
            subtopic=cluster.get("label") or f"Cluster {cluster_id + 1}",
            category=cluster.get("top_categories") or "General",
            article_count=int(cluster.get("article_count") or len(articles)),
            first_seen=None,
            last_seen=None,
            span_days=None,
            entry_ids=[a.entry_id for a in articles],
            titles=[a.title for a in articles],
            hype_start=cluster.get("avg_hype"),
            hype_end=cluster.get("avg_hype"),
            hype_trend=0.0,
            avg_importance=cluster.get("avg_importance"),
            avg_hype=cluster.get("avg_hype"),
            avg_credibility=cluster.get("avg_credibility"),
            latest_title=articles[0].title if articles else None,
            articles=articles,
        )
        _detail_cache[arc_id] = detail
        return detail

    rows = query(
        f"""
        SELECT
            arc_id,
            subtopic,
            category,
            article_count,
            first_seen,
            last_seen,
            span_days,
            entry_ids,
            titles,
            hype_start,
            hype_end,
            hype_trend,
            avg_importance,
            avg_hype,
            avg_credibility,
            latest_title
        FROM serve.story_arcs
        WHERE arc_id = '{arc_id}'
        LIMIT 1
        """
    )

    if not rows:
        raise HTTPException(status_code=404, detail="Narrative arc not found")

    arc_row = rows[0]
    entry_ids: list[str] = json.loads(arc_row.get("entry_ids") or "[]")
    titles: list[str] = json.loads(arc_row.get("titles") or "[]")

    # Fetch full article cards for timeline, preserving published_at order
    articles: list[ArticleCard] = []
    if entry_ids:
        ids_sql = ", ".join(f"'{eid}'" for eid in entry_ids)
        art_rows = query(
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
            WHERE entry_id IN ({ids_sql})
            ORDER BY published_at ASC
            """
        )
        articles = [ArticleCard(**r) for r in art_rows]

    detail = NarrativeDetail(
        arc_id=arc_row["arc_id"],
        subtopic=arc_row["subtopic"],
        category=arc_row.get("category"),
        article_count=arc_row["article_count"],
        first_seen=arc_row.get("first_seen"),
        last_seen=arc_row.get("last_seen"),
        span_days=arc_row.get("span_days"),
        entry_ids=entry_ids,
        titles=titles,
        hype_start=arc_row.get("hype_start"),
        hype_end=arc_row.get("hype_end"),
        hype_trend=arc_row.get("hype_trend"),
        avg_importance=arc_row.get("avg_importance"),
        avg_hype=arc_row.get("avg_hype"),
        avg_credibility=arc_row.get("avg_credibility"),
        latest_title=arc_row.get("latest_title"),
        articles=articles,
    )

    _detail_cache[arc_id] = detail
    return detail
