"""
SmartNews Live Data Quality Checks
=================================
Detects subtle production regressions that may not surface as HTTP failures.

Usage:
  python tests/live_data_quality.py [base_url]

Exit codes:
  0 = pass
  1 = fail
"""
from __future__ import annotations

import json
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else "https://smartnews-api.onrender.com").rstrip("/")
TIMEOUT = 30
RETRIES = 3

fails: list[str] = []
warns: list[str] = []


def fetch(path: str, params: dict | None = None):
    url = BASE_URL + path
    if params:
        url += "?" + urllib.parse.urlencode(params)

    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            if attempt < RETRIES:
                time.sleep(2 * attempt)
                continue
            raise
        except urllib.error.HTTPError as err:
            if err.code in (502, 503, 504) and attempt < RETRIES:
                time.sleep(2 * attempt)
                continue
            raise


def fail(msg: str):
    fails.append(msg)


def warn(msg: str):
    warns.append(msg)


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        value = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def check_home():
    status, data = fetch("/api/home")
    if status != 200:
        fail(f"/api/home status={status}")
        return

    top = data.get("top_stories") or []
    if len(top) < 5:
        fail(f"/api/home top_stories too low: {len(top)}")

    ids = [x.get("entry_id") for x in top if x.get("entry_id")]
    if len(ids) != len(set(ids)):
        fail("/api/home has duplicate entry_id values in top_stories")

    for idx, item in enumerate(top):
        title = (item.get("title") or "").strip()
        if not title:
            fail(f"/api/home top_stories[{idx}] missing title")

        for key in ("hype_score", "credibility_score", "importance_score"):
            val = item.get(key)
            if val is None or not (0 <= val <= 1):
                fail(f"/api/home top_stories[{idx}] invalid {key}={val}")

    now = datetime.now(timezone.utc)
    fresh_count = 0
    for item in top:
        dt = parse_dt(item.get("published_at") or "")
        if dt and (now - dt).total_seconds() <= 72 * 3600:
            fresh_count += 1
    if fresh_count == 0:
        warn("/api/home has no items published within last 72h")


def check_categories():
    status, data = fetch("/api/categories")
    if status != 200:
        fail(f"/api/categories status={status}")
        return

    categories = data.get("categories") or []
    if not categories:
        fail("/api/categories returned empty list")
        return

    slug_re = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    for c in categories:
        slug = c.get("slug") or ""
        if not slug_re.match(slug):
            fail(f"/api/categories invalid slug format: {slug}")
        if (c.get("article_count") or 0) < 0:
            fail(f"/api/categories negative article_count for slug={slug}")


def check_sources():
    status, data = fetch("/api/sources/leaderboard")
    if status != 200:
        fail(f"/api/sources/leaderboard status={status}")
        return

    sources = data.get("sources") or []
    if len(sources) < 3:
        warn(f"/api/sources/leaderboard low source count: {len(sources)}")

    unenriched = [s for s in sources if s.get("avg_credibility") == 0.5]
    if unenriched:
        fail(f"/api/sources/leaderboard has {len(unenriched)} unenriched default rows")


def check_stories():
    status, data = fetch("/api/stories", {"limit": 5})
    if status != 200:
        fail(f"/api/stories status={status}")
        return

    items = data.get("items") or []
    if not items:
        warn("/api/stories returned no items")
        return

    story_id = items[0].get("story_id")
    if not story_id:
        fail("/api/stories first item missing story_id")
        return

    s, detail = fetch(f"/api/story/{urllib.parse.quote(story_id, safe='')}")
    if s != 200:
        fail(f"/api/story/{{id}} status={s}")
        return

    body = (detail.get("compiled_body") or "").strip().lower()
    if not body:
        fail("/api/story/{id} has empty compiled_body")
    if "pending" in body or "synthesis pending" in body:
        fail("/api/story/{id} contains placeholder pending text")

    if len((detail.get("source_articles") or [])) == 0:
        warn("/api/story/{id} has zero source_articles")


def main():
    t0 = time.time()
    try:
        check_home()
        check_categories()
        check_sources()
        check_stories()
    except Exception as err:
        fail(f"Unhandled error: {err}")

    elapsed = int((time.time() - t0) * 1000)

    print("\nLive Data Quality Report")
    print(f"Target: {BASE_URL}")
    print(f"Elapsed: {elapsed}ms")

    if warns:
        print("Warnings:")
        for w in warns:
            print(f" - {w}")

    if fails:
        print("Failures:")
        for f in fails:
            print(f" - {f}")
        sys.exit(1)

    print("Status: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
