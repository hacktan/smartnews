"""
Story Claim Verification endpoints.

GET /api/story/{story_id}/claims - grouped claims with verdicts.
"""

from fastapi import APIRouter
from cachetools import TTLCache

from ..db import query
from ..models import StoryClaim, StoryClaimsResponse

router = APIRouter()

_claims_cache: TTLCache = TTLCache(maxsize=100, ttl=180)


@router.get("/story/{story_id}/claims", response_model=StoryClaimsResponse)
def get_story_claims(story_id: str):
    if story_id in _claims_cache:
        return _claims_cache[story_id]

    rows = query(
        """
        SELECT
            story_id,
            claim_group_id,
            claim_text,
            claim_normalized,
            verdict,
            confidence,
            confirm_count,
            dispute_count,
            sources_confirming,
            sources_disputing,
            entry_ids
        FROM serve.story_claims
        WHERE story_id = ?
        ORDER BY
            CASE verdict
                WHEN 'DISPUTED' THEN 0
                WHEN 'CONSENSUS' THEN 1
                ELSE 2
            END,
            confidence DESC,
            confirm_count DESC
        """,
        (story_id,),
    )

    items = [StoryClaim(**r) for r in rows]
    result = StoryClaimsResponse(story_id=story_id, items=items, total=len(items))
    _claims_cache[story_id] = result
    return result
