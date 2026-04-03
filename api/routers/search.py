"""
GET /api/search?q=<term>&category=<slug>&source=<name>&days=<int>

Keyword search against title + summary_snippet in serve.article_cards.
Filters: category slug, source_name, published within last N days.
Results ordered by importance_score DESC then published_at DESC.
"""
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Query as QParam, HTTPException
from typing import Optional

from ..db import query
from ..config import settings
from ..models import SearchResponse, ArticleCard
from .categories import _slug_to_label

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/search", response_model=SearchResponse)
def search_articles(
    q: str = QParam(min_length=1, max_length=200),
    category: Optional[str] = QParam(default=None),
    source: Optional[str] = QParam(default=None, max_length=100),
    days: Optional[int] = QParam(default=None, ge=1, le=365),
    min_credibility: Optional[float] = QParam(default=None, ge=0.0, le=1.0),
    max_hype: Optional[float] = QParam(default=None, ge=0.0, le=1.0),
    min_importance: Optional[float] = QParam(default=None, ge=0.0, le=1.0),
):
    max_results = settings.search_max_results

    # Build WHERE clauses and params dynamically
    conditions = [
        "(LOWER(title) LIKE ? OR LOWER(summary_snippet) LIKE ?)"
    ]
    like_term = f"%{q.lower()}%"
    params: list = [like_term, like_term]

    if category:
        label = _slug_to_label(category)
        if label is None:
            raise HTTPException(status_code=400, detail=f"Unknown category slug: '{category}'")
        conditions.append("category = ?")
        params.append(label)

    if source:
        conditions.append("LOWER(source_name) LIKE ?")
        params.append(f"%{source.lower()}%")

    if days:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        conditions.append("published_at >= ?")
        params.append(cutoff)
    
    if min_credibility is not None:
        conditions.append("credibility_score >= ?")
        params.append(min_credibility)
    
    if max_hype is not None:
        conditions.append("hype_score <= ?")
        params.append(max_hype)

    if min_importance is not None:
        conditions.append("importance_score >= ?")
        params.append(min_importance)

    where_clause = " AND ".join(conditions)

    count_rows = query(
        f"SELECT COUNT(*) AS total FROM serve.article_cards WHERE {where_clause}",
        tuple(params),
    )
    total = count_rows[0]["total"] if count_rows else 0

    rows = query(
        f"""
        SELECT entry_id, title, source_name, published_at, category,
               summary_snippet, hype_score, credibility_score, importance_score,
               link, CAST(publish_date AS STRING) AS publish_date, image_url
        FROM serve.article_cards
        WHERE {where_clause}
        ORDER BY importance_score DESC NULLS LAST, published_at DESC
        LIMIT {max_results}
        """,
        tuple(params),
    )

    return SearchResponse(
        query=q,
        total=total,
        items=[ArticleCard(**r) for r in rows],
    )
