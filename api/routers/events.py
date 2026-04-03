"""
POST /api/events/click   — article click tracking
POST /api/events/save    — bookmark
POST /api/events/hide    — not-interested signal
POST /api/events/dwell   — reading time capture

Events are logged to application logs for now (Phase 1).
A future pipeline will consume these to build user profiles (Layer 6).
We return 200 immediately so the frontend fire-and-forget pattern works.
"""
import logging
from fastapi import APIRouter

from ..models import ClickEvent, SaveEvent, HideEvent, DwellEvent, EventResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/events/click", response_model=EventResponse)
def track_click(event: ClickEvent):
    logger.info(
        "event=click entry_id=%s session=%s source=%s",
        event.entry_id, event.session_id, event.source,
    )
    return EventResponse()


@router.post("/events/save", response_model=EventResponse)
def track_save(event: SaveEvent):
    logger.info(
        "event=save entry_id=%s session=%s",
        event.entry_id, event.session_id,
    )
    return EventResponse()


@router.post("/events/hide", response_model=EventResponse)
def track_hide(event: HideEvent):
    logger.info(
        "event=hide entry_id=%s session=%s reason=%s",
        event.entry_id, event.session_id, event.reason,
    )
    return EventResponse()


@router.post("/events/dwell", response_model=EventResponse)
def track_dwell(event: DwellEvent):
    logger.info(
        "event=dwell entry_id=%s session=%s seconds=%d",
        event.entry_id, event.session_id, event.seconds,
    )
    return EventResponse()
