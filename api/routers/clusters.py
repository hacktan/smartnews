"""
GET /api/clusters       — list all story clusters with aggregate stats
GET /api/clusters/{id}  — cluster detail with article cards
"""
import logging
from fastapi import APIRouter, HTTPException
from cachetools import TTLCache

from ..db import query
from ..config import settings
from ..models import StoryCluster, StoryClusterDetail, ArticleCard

router = APIRouter()
logger = logging.getLogger(__name__)

_clusters_cache: TTLCache = TTLCache(maxsize=4, ttl=settings.cache_ttl_seconds)


@router.get("/clusters", response_model=list[StoryCluster])
def list_clusters():
    if "all" in _clusters_cache:
        return _clusters_cache["all"]

    rows = query("""
        SELECT cluster_id, label, article_count, top_entry_ids,
               top_categories, avg_importance, avg_credibility, avg_hype
        FROM serve.story_clusters
        ORDER BY avg_importance DESC
    """)
    result = [StoryCluster(**dict(r)) for r in rows]
    _clusters_cache["all"] = result
    return result


@router.get("/clusters/{cluster_id}", response_model=StoryClusterDetail)
def get_cluster(cluster_id: int):
    cache_key = f"cluster_{cluster_id}"
    if cache_key in _clusters_cache:
        return _clusters_cache[cache_key]

    meta_rows = query(
        """
        SELECT cluster_id, label, article_count, top_entry_ids,
               top_categories, avg_importance, avg_credibility, avg_hype
        FROM serve.story_clusters
        WHERE cluster_id = ?
        LIMIT 1
        """,
        (cluster_id,),
    )
    if not meta_rows:
        raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} not found.")

    meta = dict(meta_rows[0])
    primary_topic_rows = query(
        """
        SELECT COALESCE(NULLIF(subtopic, ''), category) AS primary_topic, COUNT(*) AS c
        FROM serve.article_detail
        WHERE cluster_id = ?
        GROUP BY COALESCE(NULLIF(subtopic, ''), category)
        ORDER BY c DESC
        LIMIT 1
        """,
        (cluster_id,),
    )
    meta["primary_topic"] = (
        primary_topic_rows[0]["primary_topic"] if primary_topic_rows else None
    )

    article_rows = query(
        """
        SELECT entry_id, title, source_name, published_at, category,
               summary_snippet, hype_score, credibility_score, importance_score,
               link, CAST(publish_date AS STRING) AS publish_date, image_url
        FROM serve.article_cards
        WHERE cluster_id = ?
        ORDER BY importance_score DESC
        LIMIT 20
        """,
        (cluster_id,),
    )
    articles = [ArticleCard(**dict(r)) for r in article_rows]

    result = StoryClusterDetail(**meta, articles=articles)
    _clusters_cache[cache_key] = result
    return result
