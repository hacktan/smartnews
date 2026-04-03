"""
GET /api/categories        — list all categories with article counts
GET /api/category/{slug}   — paginated article feed for one category

Category slugs are derived by lowercasing and replacing spaces/& with hyphens.
Example: "AI & Machine Learning" → "ai-machine-learning"
"""
import logging
from fastapi import APIRouter, HTTPException, Query
from cachetools import TTLCache

from ..db import query
from ..config import settings
from ..models import CategoriesResponse, CategoryMeta, CategoryFeedResponse, CategoryFeedItem

router = APIRouter()
logger = logging.getLogger(__name__)

_categories_cache: TTLCache = TTLCache(maxsize=1, ttl=settings.cache_ttl_seconds)
_feed_cache: TTLCache = TTLCache(maxsize=50, ttl=settings.cache_ttl_seconds)

# Canonical category labels (matches Silver transformation)
CATEGORY_LABELS = [
    "AI & Machine Learning",
    "Cloud & Infrastructure",
    "Cybersecurity",
    "Mobile & Apps",
    "Data & Analytics",
    "Software Development",
    "Hardware & Devices",
    "Business & Startups",
    "General Tech",
]


def _slug_to_label(slug: str) -> str | None:
    for label in CATEGORY_LABELS:
        if _label_to_slug(label) == slug:
            return label
    return None


def _label_to_slug(label: str) -> str:
    return (
        label.lower()
        .replace(" & ", "-")
        .replace(" ", "-")
        .replace("&", "-")
    )


@router.get("/categories", response_model=CategoriesResponse)
def get_categories():
    if "categories" in _categories_cache:
        return _categories_cache["categories"]

    rows = query(
        """
        SELECT category, COUNT(*) AS article_count
        FROM serve.category_feeds
        GROUP BY category
        ORDER BY article_count DESC
        """
    )
    count_map = {r["category"]: r["article_count"] for r in rows}

    categories = [
        CategoryMeta(
            slug=_label_to_slug(label),
            label=label,
            article_count=count_map.get(label, 0),
        )
        for label in CATEGORY_LABELS
        if count_map.get(label, 0) > 0
    ]

    result = CategoriesResponse(categories=categories)
    _categories_cache["categories"] = result
    return result


@router.get("/category/{slug}", response_model=CategoryFeedResponse)
def get_category_feed(
    slug: str,
    page: int = Query(default=1, ge=1),
    sort: str = Query(default="importance", pattern="^(importance|recency)$"),
):
    label = _slug_to_label(slug)
    if label is None:
        raise HTTPException(status_code=404, detail=f"Category '{slug}' not found.")

    cache_key = f"{slug}:{page}:{sort}"
    if cache_key in _feed_cache:
        return _feed_cache[cache_key]

    page_size = settings.category_page_size
    offset = (page - 1) * page_size
    order_col = "importance_score DESC" if sort == "importance" else "published_at DESC"

    count_rows = query(
        "SELECT COUNT(*) AS total FROM serve.category_feeds WHERE category = ?",
        (label,),
    )
    total = count_rows[0]["total"] if count_rows else 0

    rows = query(
        f"""
        SELECT entry_id, category, published_at, importance_score, hype_score,
               credibility_score, title, summary_snippet, source_name, image_url
        FROM serve.category_feeds
        WHERE category = ?
        ORDER BY {order_col}
        LIMIT {page_size} OFFSET {offset}
        """,
        (label,),
    )

    result = CategoryFeedResponse(
        category=label,
        page=page,
        page_size=page_size,
        total=total,
        items=[CategoryFeedItem(**r) for r in rows],
    )
    _feed_cache[cache_key] = result
    return result
