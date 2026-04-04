"""
SmartNews API — main FastAPI application

Startup:
  - DuckDB file is downloaded from GitHub Releases if missing
  - On shutdown the connection is closed cleanly

All routes are prefixed with /api.
CORS is configured via the CORS_ORIGINS env var (comma-separated origins).

Note: this file may receive no-op commits to force Render redeploy when DB release asset is refreshed.
Deploy marker: 2026-04-04 source-expansion refresh.
Deploy marker: 2026-04-04 broad-news expansion refresh.
"""
import logging
import os
import urllib.error
import urllib.request
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import close_connection
from .routers import (
    home_router,
    categories_router,
    articles_router,
    search_router,
    events_router,
    sources_router,
    clusters_router,
    entities_router,
    insights_router,
    briefing_router,
    topics_router,
    narratives_router,
    stories_router,
    claims_router,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def _download_db_from_github(db_path: str) -> None:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        logger.info("GITHUB_TOKEN not set; attempting unauthenticated GitHub download.")

    api_url = f"https://api.github.com/repos/{settings.github_repository}/releases/tags/{settings.github_release_tag}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "smartnews-api",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(api_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            release = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Failed to fetch release metadata: {err.code} {body}. "
            "If repository is private or rate-limited, set GITHUB_TOKEN."
        ) from err

    asset_url = None
    for asset in release.get("assets", []):
        if asset.get("name") == settings.github_db_asset_name:
            asset_url = asset.get("browser_download_url")
            break

    if not asset_url:
        raise RuntimeError(
            f"Release '{settings.github_release_tag}' does not contain asset '{settings.github_db_asset_name}'."
        )

    download_req = urllib.request.Request(asset_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(download_req, timeout=60) as resp:
            data = resp.read()
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Failed to download DB asset: {err.code} {body}. "
            "If repository is private or rate-limited, set GITHUB_TOKEN."
        ) from err

    with open(db_path, "wb") as f:
        f.write(data)


def _sync_db_from_github(db_path: str) -> None:
    """Download latest DB asset atomically and replace local DB file."""
    tmp_path = f"{db_path}.download"
    _download_db_from_github(tmp_path)
    os.replace(tmp_path, db_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Keep API in sync with latest release-backed DB unless explicitly disabled.
    if settings.db_sync_on_startup:
        try:
            logger.info("Syncing database from GitHub Releases on startup...")
            _sync_db_from_github(settings.db_path)
            logger.info("Database synced: %s", settings.db_path)
        except Exception as err:
            if os.path.exists(settings.db_path):
                logger.warning(
                    "DB sync failed, continuing with local DB at %s (%s)",
                    settings.db_path,
                    err,
                )
            else:
                raise
    elif not os.path.exists(settings.db_path):
        logger.info("Downloading database from GitHub Releases...")
        _download_db_from_github(settings.db_path)
        logger.info("Database downloaded: %s", settings.db_path)
    logger.info("SmartNews API starting up.")
    yield
    logger.info("SmartNews API shutting down.")
    close_connection()


app = FastAPI(
    title="SmartNews API",
    version="0.1.0",
    description="AI-enriched news discovery platform — serves DuckDB serve tables.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(home_router, prefix="/api")
app.include_router(categories_router, prefix="/api")
app.include_router(articles_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(sources_router, prefix="/api")
app.include_router(clusters_router, prefix="/api")
app.include_router(entities_router, prefix="/api")
app.include_router(insights_router, prefix="/api")
app.include_router(briefing_router, prefix="/api")
app.include_router(topics_router, prefix="/api")
app.include_router(narratives_router, prefix="/api")
app.include_router(stories_router, prefix="/api")
app.include_router(claims_router, prefix="/api")


@app.get("/")
def root():
    return {
        "service": "smartnews-api",
        "status": "ok",
        "health": "/health",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
